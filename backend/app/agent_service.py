from __future__ import annotations

import base64
import uuid
from collections.abc import Callable

from app.agent_openai import AgentTurnDecision
from app.agent_repository import AgentRepository, AgentSessionState
from app.agent_schemas import (
    AgentEnvelope,
    AgentMessageDto,
    AgentSessionDto,
    ImageVersionDto,
)
from app.agent_tools import AgentTool, AgentToolContext, AgentToolResult
from app.image_storage import LocalImageStorage


Planner = Callable[..., AgentTurnDecision]


class AgentServiceError(Exception):
    status_code = 500


class AgentInputError(AgentServiceError):
    status_code = 400


class ImageAgentService:
    def __init__(
        self,
        repo: AgentRepository,
        storage: LocalImageStorage,
        planner: Planner,
        tools: dict[str, AgentTool],
    ) -> None:
        self.repo = repo
        self.storage = storage
        self.planner = planner
        self.tools = tools

    def create_session(
        self,
        instruction: str,
        image_bytes: bytes,
        image_name: str,
        mime_type: str,
        size: str,
    ) -> AgentEnvelope:
        if not instruction.strip():
            raise AgentInputError("Please enter an edit instruction.")
        if not image_bytes:
            raise AgentInputError("Please upload the initial product image.")

        session = self.repo.create_session(title=instruction[:80] or "Image session")
        stored = self.storage.write_image(image_bytes, mime_type=mime_type)
        initial = self.repo.add_image_version(
            session.id,
            None,
            stored.storage_key,
            stored.mime_type,
            "Initial upload",
            "user-upload",
        )
        self.repo.set_current_version(session.id, initial.id)
        self.repo.add_message(session.id, "user", instruction)
        return self._run_turn(session.id, instruction, size)

    def send_message(
        self, session_id: uuid.UUID, instruction: str, size: str
    ) -> AgentEnvelope:
        if not instruction.strip():
            raise AgentInputError("Please enter an edit instruction.")
        state = self.repo.get_session_state(session_id)
        if state is None:
            raise AgentInputError("Session not found.")
        if self._current_version(state) is None:
            raise AgentInputError("Session has no active image.")

        self.repo.add_message(session_id, "user", instruction)
        return self._run_turn(session_id, instruction, size)

    def restore_version(
        self, session_id: uuid.UUID, version_id: uuid.UUID
    ) -> AgentEnvelope:
        state = self.repo.get_session_state(session_id)
        if state is None:
            raise AgentInputError("Session not found.")
        if not any(version.id == version_id for version in state.versions):
            raise AgentInputError("Image version not found.")

        self.repo.restore_version(session_id, version_id)
        state = self.repo.get_session_state(session_id)
        return self._envelope(state)

    def get_session(self, session_id: uuid.UUID) -> AgentEnvelope:
        state = self.repo.get_session_state(session_id)
        if state is None:
            raise AgentInputError("Session not found.")
        return self._envelope(state)

    def _run_turn(self, session_id: uuid.UUID, instruction: str, size: str) -> AgentEnvelope:
        state = self.repo.get_session_state(session_id)
        if state is None:
            raise AgentInputError("Session not found.")
        current = self._current_version(state)
        if current is None:
            raise AgentInputError("Session has no active image.")

        decision = self.planner(
            user_message=instruction,
            current_image_summary=f"Active image version {current.id}",
            recent_messages=[
                {"role": message.role, "content": message.content}
                for message in state.messages[-8:]
            ],
            previous_response_id=state.session.previous_response_id,
        )
        if decision.action == "clarify":
            self.repo.set_previous_response_id(session_id, decision.response_id)
            self.repo.add_message(
                session_id,
                "assistant",
                decision.assistant_message,
                response_id=decision.response_id,
            )
            return self._envelope(
                self.repo.get_session_state(session_id),
                pending_question=decision.assistant_message,
            )

        tool = self.tools.get(decision.tool_name or "")
        if tool is None:
            raise AgentServiceError("The selected agent tool is not available.")

        result: AgentToolResult = tool.execute(
            AgentToolContext(
                image_bytes=self.storage.read_image(current.storage_key),
                image_name=current.storage_key,
                mime_type=current.mime_type,
                instruction=decision.tool_instruction or instruction,
                size=size,
            )
        )
        stored = self.storage.write_image(result.image_bytes, result.mime_type)
        version = self.repo.add_image_version(
            session_id,
            current.id,
            stored.storage_key,
            stored.mime_type,
            result.prompt,
            result.model,
            revised_prompt=result.revised_prompt,
        )
        self.repo.set_current_version(session_id, version.id)
        self.repo.set_previous_response_id(session_id, decision.response_id)
        self.repo.add_message(
            session_id,
            "assistant",
            decision.assistant_message,
            response_id=decision.response_id,
        )
        return self._envelope(self.repo.get_session_state(session_id))

    def _current_version(self, state: AgentSessionState):
        return next(
            (
                version
                for version in state.versions
                if version.id == state.session.current_version_id
            ),
            None,
        )

    def _src_for_storage_key(self, storage_key: str, mime_type: str) -> str:
        encoded = base64.b64encode(self.storage.read_image(storage_key)).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _envelope(
        self, state: AgentSessionState | None, pending_question: str | None = None
    ) -> AgentEnvelope:
        if state is None:
            raise AgentInputError("Session not found.")
        versions = [
            ImageVersionDto(
                id=version.id,
                sessionId=version.session_id,
                parentVersionId=version.parent_version_id,
                src=self._src_for_storage_key(version.storage_key, version.mime_type),
                storageKey=version.storage_key,
                mimeType=version.mime_type,
                width=version.width,
                height=version.height,
                prompt=version.prompt,
                revisedPrompt=version.revised_prompt,
                model=version.model,
                createdAt=version.created_at,
            )
            for version in state.versions
        ]
        current = next(
            (version for version in versions if version.id == state.session.current_version_id),
            None,
        )
        return AgentEnvelope(
            session=AgentSessionDto(
                id=state.session.id,
                title=state.session.title,
                currentVersionId=state.session.current_version_id,
                previousResponseId=state.session.previous_response_id,
                status=state.session.status,
                createdAt=state.session.created_at,
                updatedAt=state.session.updated_at,
            ),
            messages=[
                AgentMessageDto(
                    id=message.id,
                    sessionId=message.session_id,
                    role=message.role,
                    content=message.content,
                    responseId=message.response_id,
                    toolCallId=message.tool_call_id,
                    createdAt=message.created_at,
                )
                for message in state.messages
            ],
            currentImage=current,
            versions=versions,
            pendingQuestion=pending_question,
            error=None,
        )
