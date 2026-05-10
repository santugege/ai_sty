from __future__ import annotations

import base64
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

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
from app.agent_tools import AgentTool, AgentToolContext, AgentToolResult


Planner = Callable[..., ConversationTurnDecision]
Summarizer = Callable[..., str]


class AgentServiceError(Exception):
    status_code = 500


class ConversationInputError(AgentServiceError):
    status_code = 400


AgentInputError = ConversationInputError


@dataclass
class StoredAttachment:
    id: str
    name: str
    mime_type: str
    image_bytes: bytes
    created_at: datetime


@dataclass
class StoredImage:
    id: str
    image_bytes: bytes
    mime_type: str
    prompt: str
    revised_prompt: str | None
    model: str
    created_at: datetime


@dataclass
class _PersistentImageSource:
    image_bytes: bytes
    mime_type: str
    name: str


@dataclass
class StoredMessage:
    id: str
    role: str
    content: str
    attachments: list[StoredAttachment] = field(default_factory=list)
    response_id: str | None = None
    image: StoredImage | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ConversationState:
    id: str = "default"
    title: str = "ChatGPT 对话"
    previous_response_id: str | None = None
    status: str = "ready"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    messages: list[StoredMessage] = field(default_factory=list)
    current_image: StoredImage | None = None


class ChatGptConversationService:
    def __init__(
        self,
        planner: Planner,
        tools: dict[str, AgentTool],
        repo: AgentRepository | None = None,
        storage: object | None = None,
        summarizer: Summarizer | None = None,
        state: ConversationState | None = None,
    ) -> None:
        self.planner = planner
        self.tools = tools
        self.repo = repo
        self.storage = storage
        self.summarizer = summarizer
        self.state = state or ConversationState()

    def send_message(
        self,
        *args,
        **kwargs,
    ) -> AgentEnvelope:
        if self.repo is None:
            return self._send_in_memory_message(*args, **kwargs)
        return self._send_persistent_message(*args, **kwargs)

    def _send_in_memory_message(
        self,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
    ) -> AgentEnvelope:
        normalized_message = message.strip()
        if not normalized_message and not attachments:
            raise ConversationInputError("请输入消息或上传图片。")

        stored_attachments = [
            StoredAttachment(
                id=_new_id("att"),
                name=str(attachment["image_name"]),
                mime_type=str(attachment["mime_type"]),
                image_bytes=bytes(attachment["image_bytes"]),
                created_at=datetime.now(UTC),
            )
            for attachment in attachments
        ]
        user_message = StoredMessage(
            id=_new_id("msg"),
            role="user",
            content=normalized_message,
            attachments=stored_attachments,
            created_at=datetime.now(UTC),
        )
        self.state.messages.append(user_message)
        if stored_attachments:
            latest_attachment = stored_attachments[-1]
            self.state.current_image = StoredImage(
                id=_new_id("img"),
                image_bytes=latest_attachment.image_bytes,
                mime_type=latest_attachment.mime_type,
                prompt=normalized_message or "Uploaded image",
                revised_prompt=None,
                model="user-upload",
                created_at=latest_attachment.created_at,
            )
        self.state.updated_at = datetime.now(UTC)

        decision = self.planner(
            user_message=normalized_message,
            recent_messages=[
                {"role": item.role, "content": item.content}
                for item in self.state.messages[-12:]
            ],
            has_current_image=self.state.current_image is not None,
            uploaded_image_count=len(stored_attachments),
            previous_response_id=self.state.previous_response_id,
        )

        if decision.action in {"answer", "clarify"}:
            self._append_assistant_message(
                content=decision.assistant_message,
                response_id=decision.response_id,
            )
            self.state.previous_response_id = decision.response_id
            return self._envelope()

        image_source = stored_attachments[-1] if stored_attachments else self.state.current_image
        if image_source is None:
            self.state.messages.pop()
            raise ConversationInputError("请先上传一张图片。")

        tool = self.tools.get(decision.tool_name or "")
        if tool is None:
            raise AgentServiceError("The selected agent tool is not available.")

        result = self._execute_image_tool(tool, decision, image_source, size)
        current_image = StoredImage(
            id=_new_id("img"),
            image_bytes=result.image_bytes,
            mime_type=result.mime_type,
            prompt=result.prompt,
            revised_prompt=result.revised_prompt,
            model=result.model,
            created_at=datetime.now(UTC),
        )
        self.state.current_image = current_image
        self.state.previous_response_id = decision.response_id
        self._append_assistant_message(
            content=decision.assistant_message,
            response_id=decision.response_id,
            image=current_image,
        )
        return self._envelope()

    def create_session(
        self,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
    ) -> AgentEnvelope:
        if self.repo is None:
            return self._send_in_memory_message(message, attachments, size)
        if not message.strip() and not attachments:
            raise ConversationInputError("Please enter a message or upload an image.")
        session = self.repo.create_session(_title_from_message(message))
        try:
            return self._send_persistent_message(session.id, message, attachments, size)
        except Exception:
            self.repo.delete_session(session.id)
            raise

    def send_session_message(
        self,
        session_id: str | uuid.UUID,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
    ) -> AgentEnvelope:
        return self._send_persistent_message(session_id, message, attachments, size)

    def list_sessions(self) -> ConversationListEnvelope:
        if self.repo is None:
            return ConversationListEnvelope(sessions=[])
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
    ) -> AgentEnvelope:
        if self.repo is None or self.storage is None:
            raise AgentServiceError("Persistent agent service is not configured.")

        normalized_message = message.strip()
        if not normalized_message and not attachments:
            raise ConversationInputError("Please enter a message or upload an image.")

        state = self._get_persistent_state(session_id)
        parsed_session_id = state.session.id
        restored_current_version_id = state.session.current_version_id
        restored_previous_response_id = state.session.previous_response_id
        restored_summary = state.session.summary
        restored_summary_updated_at = state.session.summary_updated_at
        parent_version = _current_version(state)
        uploaded_versions: list[ImageVersionRow] = []
        persisted_message_ids: list[uuid.UUID] = []
        persisted_version_ids: list[uuid.UUID] = []
        persisted_storage_keys: list[str] = []
        try:
            for attachment in attachments:
                stored = self.storage.write_image(
                    bytes(attachment["image_bytes"]),
                    mime_type=str(attachment["mime_type"]),
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

            linked_user_version_id = uploaded_versions[-1].id if uploaded_versions else None
            user_message = self.repo.add_message(
                parsed_session_id,
                role="user",
                content=normalized_message,
                image_version_ids=[version.id for version in uploaded_versions],
            )
            persisted_message_ids.append(user_message.id)
            if state.messages:
                self._ensure_message_after(user_message, state.messages[-1])

            state = self._get_persistent_state(parsed_session_id)
            current_version = _current_version(state)
            decision = self.planner(
                user_message=normalized_message,
                summary=state.session.summary,
                recent_messages=_recent_message_dicts(state.messages),
                has_current_image=current_version is not None,
                uploaded_image_count=len(uploaded_versions),
                previous_response_id=state.session.previous_response_id,
            )

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
                return self.get_session(parsed_session_id)

            if current_version is None:
                raise ConversationInputError("Please upload an image first.")

            tool = self.tools.get(decision.tool_name or "")
            if tool is None:
                raise AgentServiceError("The selected agent tool is not available.")

            image_bytes = self.storage.read_image(current_version.storage_key)
            result = self._execute_image_tool(
                tool,
                decision,
                _PersistentImageSource(
                    image_bytes=image_bytes,
                    mime_type=current_version.mime_type,
                    name="current-image.png",
                ),
                size,
            )
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
            persisted_version_ids.append(generated_version.id)
            self.repo.set_current_version(parsed_session_id, generated_version.id)
            assistant_message = self.repo.add_message(
                parsed_session_id,
                role="assistant",
                content=decision.assistant_message,
                response_id=decision.response_id,
                image_version_id=generated_version.id,
            )
            persisted_message_ids.append(assistant_message.id)
            self._ensure_message_after(assistant_message, user_message)
            self.repo.set_previous_response_id(parsed_session_id, decision.response_id)
            self._maybe_refresh_summary(parsed_session_id)
            return self.get_session(parsed_session_id)
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

    def reset(self) -> AgentEnvelope:
        self.state = ConversationState()
        return self._envelope()

    def _execute_image_tool(
        self,
        tool: AgentTool,
        decision: ConversationTurnDecision,
        image_source: StoredAttachment | StoredImage | _PersistentImageSource,
        size: str,
    ) -> AgentToolResult:
        return tool.execute(
            AgentToolContext(
                image_bytes=image_source.image_bytes,
                image_name=getattr(image_source, "name", "current-image.png"),
                mime_type=image_source.mime_type,
                instruction=decision.tool_instruction or "",
                size=size,
            )
        )

    def _append_assistant_message(
        self,
        content: str,
        response_id: str | None,
        image: StoredImage | None = None,
    ) -> None:
        self.state.messages.append(
            StoredMessage(
                id=_new_id("msg"),
                role="assistant",
                content=content,
                response_id=response_id,
                image=image,
                created_at=datetime.now(UTC),
            )
        )
        self.state.updated_at = datetime.now(UTC)

    def _get_persistent_state(
        self, session_id: str | uuid.UUID
    ) -> AgentSessionState:
        if self.repo is None:
            raise ConversationInputError("Conversation not found.")
        try:
            parsed_session_id = uuid.UUID(str(session_id))
        except (TypeError, ValueError) as error:
            raise ConversationInputError("Conversation not found.") from error
        state = self.repo.get_session_state(parsed_session_id)
        if state is None:
            raise ConversationInputError("Conversation not found.")
        return state

    def _maybe_refresh_summary(self, session_id: uuid.UUID) -> None:
        if self.repo is None or self.summarizer is None:
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
        if self.repo is None or message.created_at > previous_message.created_at:
            return
        message.created_at = previous_message.created_at + timedelta(microseconds=1)
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
        if self.repo is not None:
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

    def _envelope(self) -> AgentEnvelope:
        return AgentEnvelope(
            conversation=ConversationDto(
                id=self.state.id,
                title=self.state.title,
                previousResponseId=self.state.previous_response_id,
                status=self.state.status,
                createdAt=self.state.created_at,
                updatedAt=self.state.updated_at,
            ),
            messages=[
                ConversationMessageDto(
                    id=message.id,
                    role=message.role,
                    content=message.content,
                    attachments=[
                        ConversationAttachmentDto(
                            id=attachment.id,
                            name=attachment.name,
                            mimeType=attachment.mime_type,
                            src=_data_url(attachment.image_bytes, attachment.mime_type),
                            createdAt=attachment.created_at,
                        )
                        for attachment in message.attachments
                    ],
                    responseId=message.response_id,
                    image=_image_dto(message.image),
                    createdAt=message.created_at,
                )
                for message in self.state.messages
            ],
            currentImage=_image_dto(self.state.current_image),
            error=None,
        )

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
                    createdAt=message.created_at,
                )
                for message in state.messages
            ],
            currentImage=self._version_image_dto(_current_version(state)),
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
        if self.storage is None:
            raise AgentServiceError("Persistent agent service is not configured.")
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

    def _version_image_dto(
        self, version: ImageVersionRow | None
    ) -> ConversationImageDto | None:
        if version is None:
            return None
        if self.storage is None:
            raise AgentServiceError("Persistent agent service is not configured.")
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


def _image_dto(image: StoredImage | None) -> ConversationImageDto | None:
    if image is None:
        return None
    return ConversationImageDto(
        id=image.id,
        src=_data_url(image.image_bytes, image.mime_type),
        mimeType=image.mime_type,
        prompt=image.prompt,
        revisedPrompt=image.revised_prompt,
        model=image.model,
        createdAt=image.created_at,
    )


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


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
