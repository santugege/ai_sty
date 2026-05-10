from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timezone, datetime

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
        image_version_id: uuid.UUID | None = None,
    ) -> AgentMessageRow:
        row = AgentMessageRow(
            session_id=session_id,
            role=role,
            content=content,
            response_id=response_id,
            tool_call_id=tool_call_id,
            image_version_id=image_version_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_sessions(self) -> list[AgentSessionRow]:
        return list(
            self.db.scalars(
                select(AgentSessionRow).order_by(
                    AgentSessionRow.updated_at.desc(), AgentSessionRow.created_at.desc()
                )
            )
        )

    def update_session_summary(self, session_id: uuid.UUID, summary: str) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return

        session.summary = summary
        session.summary_updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def update_session_title(self, session_id: uuid.UUID, title: str) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return

        normalized = title.strip()
        if normalized:
            session.title = normalized[:120]
            self.db.commit()

    def touch_session(self, session_id: uuid.UUID) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return

        session.updated_at = datetime.now(timezone.utc)
        self.db.commit()

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

    def delete_session(self, session_id: uuid.UUID) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return

        self.db.query(AgentMessageRow).filter(
            AgentMessageRow.session_id == session_id
        ).delete(synchronize_session=False)
        self.db.query(ImageVersionRow).filter(
            ImageVersionRow.session_id == session_id
        ).delete(synchronize_session=False)
        self.db.delete(session)
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

        return AgentSessionState(
            session=session,
            messages=messages,
            versions=_order_versions_by_parent_chain(versions),
        )

    def _get_session_version(
        self, session_id: uuid.UUID, version_id: uuid.UUID
    ) -> ImageVersionRow | None:
        return self.db.scalar(
            select(ImageVersionRow).where(
                ImageVersionRow.id == version_id,
                ImageVersionRow.session_id == session_id,
            )
        )


def _order_versions_by_parent_chain(
    versions: list[ImageVersionRow],
) -> list[ImageVersionRow]:
    children_by_parent: dict[uuid.UUID | None, list[ImageVersionRow]] = {}
    version_ids = {version.id for version in versions}
    for version in versions:
        parent_id = (
            version.parent_version_id
            if version.parent_version_id in version_ids
            else None
        )
        children_by_parent.setdefault(parent_id, []).append(version)

    for siblings in children_by_parent.values():
        siblings.sort(key=lambda item: (item.created_at, str(item.id)))

    ordered: list[ImageVersionRow] = []

    def append_branch(parent_id: uuid.UUID | None) -> None:
        for child in children_by_parent.get(parent_id, []):
            ordered.append(child)
            append_branch(child.id)

    append_branch(None)
    return ordered
