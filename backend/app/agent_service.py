from __future__ import annotations

import base64
import re
import queue
import threading
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.agent_openai import ConversationTurnDecision
from app.agent_models import AgentMessageRow, ImageVersionRow
from app.agent_repository import AgentRepository, AgentSessionState
from app.agent_schemas import (
    AgentEnvelope,
    ConversationAttachmentDto,
    ConversationDto,
    ConversationImageDto,
    ConversationListEnvelope,
    ConversationListItemDto,
    ConversationMessageDto,
)
from app.agent_tools import (
    DEFAULT_AGENT_IMAGE_QUALITY,
    AgentTool,
    AgentToolContext,
    AgentToolResult,
    normalize_agent_image_quality,
)


Planner = Callable[..., ConversationTurnDecision]
Summarizer = Callable[..., str]
AgentStreamEvent = dict[str, Any]


class AgentServiceError(Exception):
    status_code = 500


class ConversationInputError(AgentServiceError):
    status_code = 400


AgentInputError = ConversationInputError


@dataclass
class _PersistentImageSource:
    image_bytes: bytes
    mime_type: str
    name: str


MAX_AGENT_IMAGE_COUNT = 4
_IMAGE_COUNT_UNITS = "\u5f20\u5f35\u5e45\u4e2a\u500b\u6b3e\u7248\u79cd\u7a2e"
_HAN_IMAGE_COUNT_DIGITS = "\u4e00\u4e8c\u4e24\u5169\u4e09\u56db"
_ARABIC_IMAGE_COUNT_PATTERN = re.compile(
    rf"(?<!\d)([1-4])\s*(?:[{_IMAGE_COUNT_UNITS}]|poses?|images?|photos?|pictures?)",
    re.IGNORECASE,
)
_HAN_IMAGE_COUNT_PATTERN = re.compile(
    rf"([{_HAN_IMAGE_COUNT_DIGITS}])\s*(?:[{_IMAGE_COUNT_UNITS}])"
)
_HAN_IMAGE_COUNT_MAP = {
    "\u4e00": 1,
    "\u4e8c": 2,
    "\u4e24": 2,
    "\u5169": 2,
    "\u4e09": 3,
    "\u56db": 4,
}


class ChatGptConversationService:
    def __init__(
        self,
        planner: Planner,
        tools: dict[str, AgentTool],
        repo: AgentRepository,
        storage: object,
        summarizer: Summarizer | None = None,
    ) -> None:
        self.planner = planner
        self.tools = tools
        self.repo = repo
        self.storage = storage
        self.summarizer = summarizer

    def create_session(
        self,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
        quality: str = DEFAULT_AGENT_IMAGE_QUALITY,
    ) -> AgentEnvelope:
        if not message.strip() and not attachments:
            raise ConversationInputError("Please enter a message or upload an image.")
        session = self.repo.create_session(_title_from_message(message))
        try:
            return self._send_persistent_message(
                session.id,
                message,
                attachments,
                size,
                quality,
            )
        except Exception:
            self.repo.delete_session(session.id)
            raise

    def send_session_message(
        self,
        session_id: str | uuid.UUID,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
        quality: str = DEFAULT_AGENT_IMAGE_QUALITY,
    ) -> AgentEnvelope:
        return self._send_persistent_message(
            session_id,
            message,
            attachments,
            size,
            quality,
        )

    def stream_create_session(
        self,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
        quality: str = DEFAULT_AGENT_IMAGE_QUALITY,
    ) -> Iterator[AgentStreamEvent]:
        if not message.strip() and not attachments:
            raise ConversationInputError("Please enter a message or upload an image.")
        session = self.repo.create_session(_title_from_message(message))
        try:
            yield from self._send_persistent_message_events(
                session.id,
                message,
                attachments,
                size,
                quality,
                emit_session=True,
            )
        except Exception:
            self.repo.delete_session(session.id)
            raise

    def stream_session_message(
        self,
        session_id: str | uuid.UUID,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
        quality: str = DEFAULT_AGENT_IMAGE_QUALITY,
    ) -> Iterator[AgentStreamEvent]:
        yield from self._send_persistent_message_events(
            session_id,
            message,
            attachments,
            size,
            quality,
            emit_session=False,
        )

    def list_sessions(self) -> ConversationListEnvelope:
        return ConversationListEnvelope(
            sessions=[
                ConversationListItemDto(
                    id=str(session.id),
                    title=session.title,
                    summary=session.summary,
                    status=session.status,
                    createdAt=session.created_at,
                    updatedAt=session.updated_at,
                )
                for session in self.repo.list_sessions()
            ]
        )

    def get_session(self, session_id: str | uuid.UUID) -> AgentEnvelope:
        state = self._get_persistent_state(session_id)
        return self._persistent_envelope(state)

    def _send_persistent_message(
        self,
        session_id: str | uuid.UUID,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
        quality: str,
    ) -> AgentEnvelope:
        envelope = None
        for event in self._send_persistent_message_events(
            session_id,
            message,
            attachments,
            size,
            quality,
            emit_session=False,
            emit_deltas=False,
        ):
            if event["event"] == "final":
                envelope = event["data"]
        if envelope is None:
            raise AgentServiceError("Agent did not return a final response.")
        return AgentEnvelope.model_validate(envelope)

    def _send_persistent_message_events(
        self,
        session_id: str | uuid.UUID,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
        quality: str,
        emit_session: bool,
        emit_deltas: bool = True,
    ) -> Iterator[AgentStreamEvent]:
        normalized_message = message.strip()
        if not normalized_message and not attachments:
            raise ConversationInputError("Please enter a message or upload an image.")
        normalized_quality = normalize_agent_image_quality(quality)

        state = self._get_persistent_state(session_id)
        parsed_session_id = state.session.id
        restored_current_version_id = state.session.current_version_id
        restored_previous_response_id = state.session.previous_response_id
        restored_summary = state.session.summary
        restored_summary_updated_at = state.session.summary_updated_at
        parent_version = _current_version(state)
        uploaded_versions: list[ImageVersionRow] = []
        uploaded_image_inputs: list[dict[str, object]] = []
        persisted_message_ids: list[uuid.UUID] = []
        persisted_version_ids: list[uuid.UUID] = []
        persisted_storage_keys: list[str] = []
        try:
            if emit_session:
                yield {
                    "event": "session",
                    "data": {
                        "conversation": self._conversation_payload(state),
                    },
            }

            for attachment in attachments:
                image_bytes = bytes(attachment["image_bytes"])
                mime_type = str(attachment["mime_type"])
                uploaded_image_inputs.append(
                    {
                        "image_bytes": image_bytes,
                        "mime_type": mime_type,
                        "name": str(
                            attachment.get("image_name") or "uploaded-image.png"
                        ),
                    }
                )
                stored = self.storage.write_image(
                    image_bytes,
                    mime_type=mime_type,
                    prefix=f"agent-sessions/{parsed_session_id}",
                )
                persisted_storage_keys.append(stored.storage_key)
                version = self.repo.add_image_version(
                    session_id=parsed_session_id,
                    parent_version_id=(
                        parent_version.id if parent_version is not None else None
                    ),
                    storage_key=stored.storage_key,
                    mime_type=stored.mime_type,
                    prompt=normalized_message or "Uploaded image",
                    model="user-upload",
                    public_url=getattr(stored, "public_url", None),
                )
                persisted_version_ids.append(version.id)
                self.repo.set_current_version(parsed_session_id, version.id)
                parent_version = version
                uploaded_versions.append(version)

            user_message = self.repo.add_message(
                parsed_session_id,
                role="user",
                content=normalized_message,
                image_version_ids=[version.id for version in uploaded_versions],
            )
            persisted_message_ids.append(user_message.id)
            if state.messages:
                self._ensure_message_after(user_message, state.messages[-1])

            yield {
                "event": "user_message",
                "data": {
                    "message": self._message_payload(user_message),
                },
            }

            state = self._get_persistent_state(parsed_session_id)
            current_version = _current_version(state)

            planner_kwargs = {
                "user_message": normalized_message,
                "summary": state.session.summary,
                "recent_messages": _recent_message_dicts(state.messages),
                "has_current_image": current_version is not None,
                "uploaded_image_count": len(uploaded_versions),
                "previous_response_id": state.session.previous_response_id,
                "image_inputs": self._planner_image_inputs(
                    uploaded_image_inputs,
                    current_version,
                ),
            }
            if emit_deltas:
                decision = yield from self._run_planner_with_delta_events(
                    planner_kwargs
                )
            else:
                decision = self.planner(**planner_kwargs)

            if decision.action in {"answer", "clarify"}:
                assistant_message = self.repo.add_message(
                    parsed_session_id,
                    role="assistant",
                    content=decision.assistant_message,
                    response_id=decision.response_id,
                )
                persisted_message_ids.append(assistant_message.id)
                self._ensure_message_after(assistant_message, user_message)
                self.repo.set_previous_response_id(parsed_session_id, decision.response_id)
                self._maybe_refresh_summary(parsed_session_id)
                yield {
                    "event": "final",
                    "data": self.get_session(parsed_session_id).model_dump(mode="json"),
                }
                return

            if decision.action == "generate":
                tool = self.tools.get(decision.tool_name or "")
                if tool is None:
                    raise AgentServiceError("The selected agent tool is not available.")
                image_count = _requested_image_count(normalized_message)
                yield {
                    "event": "image_generation",
                    "data": {
                        "action": decision.action,
                        "stage": "generating",
                        "count": image_count,
                    },
                }
                results = self._execute_image_tool_requests(
                    tool,
                    decision,
                    _PersistentImageSource(
                        image_bytes=b"",
                        mime_type="image/png",
                        name="generated-image.png",
                    ),
                    size,
                    normalized_quality,
                    image_count,
                )
                yield {
                    "event": "image_generation",
                    "data": {
                        "action": decision.action,
                        "stage": "saving",
                        "count": image_count,
                    },
                }
                generated_versions = []
                for result in results:
                    stored = self.storage.write_image(
                        result.image_bytes,
                        mime_type=result.mime_type,
                        prefix=f"agent-sessions/{parsed_session_id}",
                    )
                    persisted_storage_keys.append(stored.storage_key)
                    generated_version = self.repo.add_image_version(
                        session_id=parsed_session_id,
                        parent_version_id=(
                            current_version.id if current_version is not None else None
                        ),
                        storage_key=stored.storage_key,
                        mime_type=stored.mime_type,
                        prompt=result.prompt,
                        model=result.model,
                        revised_prompt=result.revised_prompt,
                        public_url=getattr(stored, "public_url", None),
                    )
                    self._ensure_version_after(
                        generated_version,
                        generated_versions[-1] if generated_versions else current_version,
                    )
                    generated_versions.append(generated_version)
                    persisted_version_ids.append(generated_version.id)
                self.repo.set_current_version(
                    parsed_session_id, generated_versions[-1].id
                )
                assistant_message = self.repo.add_message(
                    parsed_session_id,
                    role="assistant",
                    content=decision.assistant_message,
                    response_id=decision.response_id,
                    image_version_ids=[
                        version.id for version in generated_versions
                    ],
                )
                persisted_message_ids.append(assistant_message.id)
                self._ensure_message_after(assistant_message, user_message)
                self.repo.set_previous_response_id(parsed_session_id, decision.response_id)
                self._maybe_refresh_summary(parsed_session_id)
                yield {
                    "event": "final",
                    "data": self.get_session(parsed_session_id).model_dump(mode="json"),
                }
                return

            if current_version is None:
                raise ConversationInputError("Please upload an image first.")

            tool = self.tools.get(decision.tool_name or "")
            if tool is None:
                raise AgentServiceError("The selected agent tool is not available.")

            image_bytes = self.storage.read_image(current_version.storage_key)
            image_count = _requested_image_count(normalized_message)
            yield {
                "event": "image_generation",
                "data": {
                    "action": decision.action,
                    "stage": "generating",
                    "count": image_count,
                },
            }
            results = self._execute_image_tool_requests(
                tool,
                decision,
                _PersistentImageSource(
                    image_bytes=image_bytes,
                    mime_type=current_version.mime_type,
                    name="current-image.png",
                ),
                size,
                normalized_quality,
                image_count,
            )
            yield {
                "event": "image_generation",
                "data": {
                    "action": decision.action,
                    "stage": "saving",
                    "count": image_count,
                },
            }
            generated_versions = []
            for result in results:
                stored = self.storage.write_image(
                    result.image_bytes,
                    mime_type=result.mime_type,
                    prefix=f"agent-sessions/{parsed_session_id}",
                )
                persisted_storage_keys.append(stored.storage_key)
                generated_version = self.repo.add_image_version(
                    session_id=parsed_session_id,
                    parent_version_id=current_version.id,
                    storage_key=stored.storage_key,
                    mime_type=stored.mime_type,
                    prompt=result.prompt,
                    model=result.model,
                    revised_prompt=result.revised_prompt,
                    public_url=getattr(stored, "public_url", None),
                )
                self._ensure_version_after(
                    generated_version,
                    generated_versions[-1] if generated_versions else current_version,
                )
                generated_versions.append(generated_version)
                persisted_version_ids.append(generated_version.id)
            self.repo.set_current_version(parsed_session_id, generated_versions[-1].id)
            assistant_message = self.repo.add_message(
                parsed_session_id,
                role="assistant",
                content=decision.assistant_message,
                response_id=decision.response_id,
                image_version_ids=[version.id for version in generated_versions],
            )
            persisted_message_ids.append(assistant_message.id)
            self._ensure_message_after(assistant_message, user_message)
            self.repo.set_previous_response_id(parsed_session_id, decision.response_id)
            self._maybe_refresh_summary(parsed_session_id)
            yield {
                "event": "final",
                "data": self.get_session(parsed_session_id).model_dump(mode="json"),
            }
            return
        except Exception:
            self._rollback_persistent_turn(
                session_id=parsed_session_id,
                message_ids=persisted_message_ids,
                version_ids=persisted_version_ids,
                storage_keys=persisted_storage_keys,
                restored_current_version_id=restored_current_version_id,
                restored_previous_response_id=restored_previous_response_id,
                restored_summary=restored_summary,
                restored_summary_updated_at=restored_summary_updated_at,
            )
            raise

    def _conversation_payload(self, state: AgentSessionState) -> dict[str, object]:
        return ConversationDto(
            id=str(state.session.id),
            title=state.session.title,
            summary=state.session.summary,
            previousResponseId=state.session.previous_response_id,
            status=state.session.status,
            createdAt=state.session.created_at,
            updatedAt=state.session.updated_at,
        ).model_dump(mode="json")

    def _message_payload(self, message: AgentMessageRow) -> dict[str, object]:
        return ConversationMessageDto(
            id=str(message.id),
            role=message.role,
            content=message.content,
            attachments=[],
            responseId=message.response_id,
            imageVersionId=(
                str(message.image_version_id)
                if message.image_version_id is not None
                else None
            ),
            image=None,
            images=[],
            createdAt=message.created_at,
        ).model_dump(mode="json")

    def _run_planner_with_delta_events(
        self,
        planner_kwargs: dict[str, object],
    ) -> Iterator[AgentStreamEvent]:
        event_queue: queue.Queue[tuple[str, object]] = queue.Queue()

        def emit_text_delta(delta: str) -> None:
            if delta:
                event_queue.put(("delta", delta))

        def run_planner() -> None:
            try:
                decision = self.planner(
                    **planner_kwargs,
                    on_text_delta=emit_text_delta,
                )
            except Exception as error:
                event_queue.put(("error", error))
                return
            event_queue.put(("decision", decision))

        worker = threading.Thread(target=run_planner, daemon=True)
        worker.start()
        while True:
            event_type, payload = event_queue.get()
            if event_type == "delta":
                yield {
                    "event": "assistant_delta",
                    "data": {"delta": payload},
                }
                continue
            worker.join()
            if event_type == "error":
                raise payload
            return payload

    def _planner_image_inputs(
        self,
        uploaded_image_inputs: list[dict[str, object]],
        current_version: ImageVersionRow | None,
    ) -> list[dict[str, object]]:
        if uploaded_image_inputs:
            return uploaded_image_inputs
        if current_version is None:
            return []
        return [
            {
                "image_bytes": self.storage.read_image(current_version.storage_key),
                "mime_type": current_version.mime_type,
                "name": "current-image.png",
            }
        ]

    def _execute_image_tool(
        self,
        tool: AgentTool,
        decision: ConversationTurnDecision,
        image_source: _PersistentImageSource,
        size: str,
        quality: str,
    ) -> AgentToolResult:
        return tool.execute(
            AgentToolContext(
                image_bytes=image_source.image_bytes,
                image_name=getattr(image_source, "name", "current-image.png"),
                mime_type=image_source.mime_type,
                instruction=decision.tool_instruction or "",
                size=size,
                quality=quality,
            )
        )

    def _execute_image_tool_requests(
        self,
        tool: AgentTool,
        decision: ConversationTurnDecision,
        image_source: _PersistentImageSource,
        size: str,
        quality: str,
        image_count: int,
    ) -> list[AgentToolResult]:
        if image_count <= 1:
            return [
                self._execute_image_tool(
                    tool,
                    decision,
                    image_source,
                    size,
                    quality,
                )
            ]

        base_instruction = decision.tool_instruction or ""

        def execute_one(index: int) -> AgentToolResult:
            return tool.execute(
                AgentToolContext(
                    image_bytes=image_source.image_bytes,
                    image_name=getattr(image_source, "name", "current-image.png"),
                    mime_type=image_source.mime_type,
                    instruction=_standalone_image_instruction(
                        base_instruction,
                        index=index,
                        total=image_count,
                    ),
                    size=size,
                    quality=quality,
                )
            )

        with ThreadPoolExecutor(max_workers=image_count) as executor:
            return list(executor.map(execute_one, range(image_count)))

    def _get_persistent_state(
        self, session_id: str | uuid.UUID
    ) -> AgentSessionState:
        try:
            parsed_session_id = uuid.UUID(str(session_id))
        except (TypeError, ValueError) as error:
            raise ConversationInputError("Conversation not found.") from error
        state = self.repo.get_session_state(parsed_session_id)
        if state is None:
            raise ConversationInputError("Conversation not found.")
        return state

    def _maybe_refresh_summary(self, session_id: uuid.UUID) -> None:
        if self.summarizer is None:
            return
        state = self.repo.get_session_state(session_id)
        if state is None or len(state.messages) < 6:
            return
        try:
            summary = self.summarizer(
                previous_summary=state.session.summary,
                recent_messages=_recent_message_dicts(state.messages),
            )
        except Exception:
            return
        if summary.strip():
            self.repo.update_session_summary(session_id, summary.strip())

    def _ensure_message_after(
        self, message: AgentMessageRow, previous_message: AgentMessageRow
    ) -> None:
        if message.created_at > previous_message.created_at:
            return
        message.created_at = previous_message.created_at + timedelta(microseconds=1)
        self.repo.db.commit()

    def _ensure_version_after(
        self,
        version: ImageVersionRow,
        previous_version: ImageVersionRow | None,
    ) -> None:
        if previous_version is None or version.created_at > previous_version.created_at:
            return
        version.created_at = previous_version.created_at + timedelta(microseconds=1)
        self.repo.db.commit()

    def _rollback_persistent_turn(
        self,
        session_id: uuid.UUID,
        message_ids: list[uuid.UUID],
        version_ids: list[uuid.UUID],
        storage_keys: list[str],
        restored_current_version_id: uuid.UUID | None,
        restored_previous_response_id: str | None,
        restored_summary: str | None,
        restored_summary_updated_at: datetime | None,
    ) -> None:
        try:
            self.repo.remove_turn_artifacts(
                session_id=session_id,
                message_ids=message_ids,
                version_ids=version_ids,
                restored_current_version_id=restored_current_version_id,
                restored_previous_response_id=restored_previous_response_id,
                restored_summary=restored_summary,
                restored_summary_updated_at=restored_summary_updated_at,
            )
        except Exception:
            pass
        delete_image = getattr(self.storage, "delete_image", None)
        if delete_image is None:
            return
        for storage_key in reversed(storage_keys):
            try:
                delete_image(storage_key)
            except Exception:
                pass

    def _persistent_envelope(self, state: AgentSessionState) -> AgentEnvelope:
        versions_by_id = {version.id: version for version in state.versions}
        return AgentEnvelope(
            conversation=ConversationDto(
                id=str(state.session.id),
                title=state.session.title,
                summary=state.session.summary,
                previousResponseId=state.session.previous_response_id,
                status=state.session.status,
                createdAt=state.session.created_at,
                updatedAt=state.session.updated_at,
            ),
            messages=[
                ConversationMessageDto(
                    id=str(message.id),
                    role=message.role,
                    content=message.content,
                    attachments=self._version_attachment_dtos(
                        message,
                        [
                            versions_by_id[version_id]
                            for version_id in state.message_image_versions.get(
                                message.id,
                                [],
                            )
                            if version_id in versions_by_id
                        ],
                        versions_by_id.get(message.image_version_id),
                    ),
                    responseId=message.response_id,
                    imageVersionId=(
                        str(message.image_version_id)
                        if message.image_version_id is not None
                        else None
                    ),
                    image=self._message_image_dto(
                        message,
                        versions_by_id.get(message.image_version_id),
                    ),
                    images=self._message_image_dtos(
                        message,
                        [
                            versions_by_id[version_id]
                            for version_id in state.message_image_versions.get(
                                message.id,
                                [],
                            )
                            if version_id in versions_by_id
                        ],
                        versions_by_id.get(message.image_version_id),
                    ),
                    createdAt=message.created_at,
                )
                for message in state.messages
            ],
            error=None,
        )

    def _version_attachment_dtos(
        self,
        message: AgentMessageRow,
        linked_versions: list[ImageVersionRow],
        fallback_version: ImageVersionRow | None,
    ) -> list[ConversationAttachmentDto]:
        if message.role != "user":
            return []
        versions = linked_versions
        if not versions and fallback_version is not None:
            versions = [fallback_version]
        return [
            ConversationAttachmentDto(
                id=str(version.id),
                name="Uploaded image",
                mimeType=version.mime_type,
                src=_data_url(
                    self.storage.read_image(version.storage_key),
                    version.mime_type,
                ),
                createdAt=version.created_at,
            )
            for version in versions
            if version.model == "user-upload"
        ]

    def _message_image_dto(
        self, message: AgentMessageRow, version: ImageVersionRow | None
    ) -> ConversationImageDto | None:
        if message.role == "user" and version is not None and version.model == "user-upload":
            return None
        return self._version_image_dto(version)

    def _message_image_dtos(
        self,
        message: AgentMessageRow,
        linked_versions: list[ImageVersionRow],
        fallback_version: ImageVersionRow | None,
    ) -> list[ConversationImageDto]:
        if message.role == "user":
            return []
        versions = linked_versions
        if not versions and fallback_version is not None:
            versions = [fallback_version]
        return [
            image
            for image in (self._version_image_dto(version) for version in versions)
            if image is not None
        ]

    def _version_image_dto(
        self, version: ImageVersionRow | None
    ) -> ConversationImageDto | None:
        if version is None:
            return None
        image_bytes = self.storage.read_image(version.storage_key)
        return ConversationImageDto(
            id=str(version.id),
            src=_data_url(image_bytes, version.mime_type),
            mimeType=version.mime_type,
            prompt=version.prompt,
            revisedPrompt=version.revised_prompt,
            model=version.model,
            createdAt=version.created_at,
        )


ImageAgentService = ChatGptConversationService


def _data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _recent_message_dicts(messages) -> list[dict[str, str]]:
    return [
        {"role": item.role, "content": item.content}
        for item in messages[-12:]
    ]


def _title_from_message(message: str) -> str:
    normalized = message.strip()
    return normalized[:60] or "New conversation"


def _current_version(state: AgentSessionState | None) -> ImageVersionRow | None:
    if state is None or state.session.current_version_id is None:
        return None
    for version in state.versions:
        if version.id == state.session.current_version_id:
            return version
    return None


def _requested_image_count(message: str) -> int:
    normalized = message.strip()
    if not normalized:
        return 1

    arabic_match = _ARABIC_IMAGE_COUNT_PATTERN.search(normalized)
    if arabic_match is not None:
        return _clamped_image_count(int(arabic_match.group(1)))

    han_match = _HAN_IMAGE_COUNT_PATTERN.search(normalized)
    if han_match is not None:
        return _HAN_IMAGE_COUNT_MAP.get(han_match.group(1), 1)

    return 1


def _clamped_image_count(value: int) -> int:
    return min(max(value, 1), MAX_AGENT_IMAGE_COUNT)


def _standalone_image_instruction(base_instruction: str, *, index: int, total: int) -> str:
    return "\n\n".join(
        [
            base_instruction.strip(),
            (
                f"Standalone output {index + 1} of {total}. "
                "Generate exactly one complete image for this output. "
                "Do not create a collage, split-screen, grid, side-by-side layout, "
                "multi-panel image, contact sheet, or picture-in-picture. "
                "Keep any requested shared character, outfit, palette, and scene "
                "consistent, but vary this output as its own standalone image."
            ),
        ]
    ).strip()
