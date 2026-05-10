from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentSessionRow(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(
        Text, nullable=False, default="Untitled image session"
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    previous_response_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    messages: Mapped[list["AgentMessageRow"]] = relationship(
        "AgentMessageRow", back_populates="session"
    )
    versions: Mapped[list["ImageVersionRow"]] = relationship(
        "ImageVersionRow",
        back_populates="session",
        foreign_keys="ImageVersionRow.session_id",
    )


class AgentMessageRow(Base):
    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_sessions.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    response_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("image_versions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[AgentSessionRow] = relationship(
        "AgentSessionRow", back_populates="messages"
    )
    image_version: Mapped[ImageVersionRow | None] = relationship(
        "ImageVersionRow", foreign_keys=[image_version_id]
    )


class ImageVersionRow(Base):
    __tablename__ = "image_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_sessions.id"), nullable=False, index=True
    )
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("image_versions.id"), nullable=True
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    revised_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    session: Mapped[AgentSessionRow] = relationship(
        "AgentSessionRow",
        back_populates="versions",
        foreign_keys=[session_id],
    )
    parent_version: Mapped[ImageVersionRow | None] = relationship(
        "ImageVersionRow", remote_side=[id]
    )
