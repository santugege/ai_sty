from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_models import AgentMessageRow, AgentSessionRow, ImageVersionRow


@dataclass(frozen=True)
class AgentSessionState:
    session: AgentSessionRow
    messages: list[AgentMessageRow]
    versions: list[ImageVersionRow]


class AgentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(self, title: str) -> AgentSessionRow:
        row = AgentSessionRow(title=title)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        response_id: str | None = None,
        tool_call_id: str | None = None,
    ) -> AgentMessageRow:
        row = AgentMessageRow(
            session_id=session_id,
            role=role,
            content=content,
            response_id=response_id,
            tool_call_id=tool_call_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def add_image_version(
        self,
        session_id: uuid.UUID,
        parent_version_id: uuid.UUID | None,
        storage_key: str,
        mime_type: str,
        prompt: str,
        model: str,
        revised_prompt: str | None = None,
        width: int | None = None,
        height: int | None = None,
        public_url: str | None = None,
    ) -> ImageVersionRow:
        row = ImageVersionRow(
            session_id=session_id,
            parent_version_id=parent_version_id,
            storage_key=storage_key,
            public_url=public_url,
            mime_type=mime_type,
            width=width,
            height=height,
            prompt=prompt,
            revised_prompt=revised_prompt,
            model=model,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def set_current_version(
        self, session_id: uuid.UUID, version_id: uuid.UUID
    ) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return

        version = self._get_session_version(session_id, version_id)
        if version is None:
            return

        session.current_version_id = version.id
        self.db.commit()

    def set_previous_response_id(
        self, session_id: uuid.UUID, response_id: str | None
    ) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return

        session.previous_response_id = response_id
        self.db.commit()

    def restore_version(self, session_id: uuid.UUID, version_id: uuid.UUID) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return

        version = self._get_session_version(session_id, version_id)
        if version is None:
            return

        session.current_version_id = version.id
        self.db.commit()

    def get_session_state(self, session_id: uuid.UUID) -> AgentSessionState | None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return None

        messages = list(
            self.db.scalars(
                select(AgentMessageRow)
                .where(AgentMessageRow.session_id == session_id)
                .order_by(AgentMessageRow.created_at, AgentMessageRow.id)
            )
        )
        versions = list(
            self.db.scalars(
                select(ImageVersionRow)
                .where(ImageVersionRow.session_id == session_id)
                .order_by(ImageVersionRow.created_at, ImageVersionRow.id)
            )
        )

        return AgentSessionState(session=session, messages=messages, versions=versions)

    def _get_session_version(
        self, session_id: uuid.UUID, version_id: uuid.UUID
    ) -> ImageVersionRow | None:
        return self.db.scalar(
            select(ImageVersionRow).where(
                ImageVersionRow.id == version_id,
                ImageVersionRow.session_id == session_id,
            )
        )
