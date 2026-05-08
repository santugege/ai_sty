from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class AgentSessionDto(BaseModel):
    id: UUID
    title: str
    currentVersionId: UUID | None
    previousResponseId: str | None
    status: str
    createdAt: datetime
    updatedAt: datetime


class AgentMessageDto(BaseModel):
    id: UUID
    sessionId: UUID
    role: Literal["user", "assistant", "tool"]
    content: str
    responseId: str | None
    toolCallId: str | None
    createdAt: datetime


class ImageVersionDto(BaseModel):
    id: UUID
    sessionId: UUID
    parentVersionId: UUID | None
    src: str
    storageKey: str
    mimeType: str
    width: int | None
    height: int | None
    prompt: str
    revisedPrompt: str | None
    model: str
    createdAt: datetime


class AgentEnvelope(BaseModel):
    session: AgentSessionDto
    messages: list[AgentMessageDto]
    currentImage: ImageVersionDto | None
    versions: list[ImageVersionDto]
    pendingQuestion: str | None = None
    error: str | None = None
