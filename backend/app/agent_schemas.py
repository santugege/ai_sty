from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ConversationDto(BaseModel):
    id: str
    title: str
    previousResponseId: str | None
    status: str
    createdAt: datetime
    updatedAt: datetime


class ConversationAttachmentDto(BaseModel):
    id: str
    name: str
    mimeType: str
    src: str
    createdAt: datetime


class ConversationImageDto(BaseModel):
    id: str
    src: str
    mimeType: str
    prompt: str
    revisedPrompt: str | None
    model: str
    createdAt: datetime


class ConversationMessageDto(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    attachments: list[ConversationAttachmentDto] = []
    responseId: str | None = None
    image: ConversationImageDto | None = None
    createdAt: datetime


class AgentEnvelope(BaseModel):
    conversation: ConversationDto
    messages: list[ConversationMessageDto]
    currentImage: ConversationImageDto | None
    error: str | None = None

