from __future__ import annotations

import base64
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.agent_openai import ConversationTurnDecision
from app.agent_schemas import (
    AgentEnvelope,
    ConversationAttachmentDto,
    ConversationDto,
    ConversationImageDto,
    ConversationMessageDto,
)
from app.agent_tools import AgentTool, AgentToolContext, AgentToolResult


Planner = Callable[..., ConversationTurnDecision]


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
        state: ConversationState | None = None,
    ) -> None:
        self.planner = planner
        self.tools = tools
        self.state = state or ConversationState()

    def send_message(
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

    def reset(self) -> AgentEnvelope:
        self.state = ConversationState()
        return self._envelope()

    def _execute_image_tool(
        self,
        tool: AgentTool,
        decision: ConversationTurnDecision,
        image_source: StoredAttachment | StoredImage,
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


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
