from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timezone, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent_models import (
    AgentMessageImageVersionRow,
    AgentMessageRow,
    AgentSessionRow,
    ImageVersionRow,
)


@dataclass(frozen=True)
class AgentSessionState:
    session: AgentSessionRow
    messages: list[AgentMessageRow]
    versions: list[ImageVersionRow]
    message_image_versions: dict[uuid.UUID, list[uuid.UUID]]


class AgentRepository:
    def __init__(self, db: Session, user_id: uuid.UUID | None = None) -> None:
        self.db = db
        self.user_id = user_id

    def create_session(
        self, title: str, user_id: uuid.UUID | None = None
    ) -> AgentSessionRow:
        owner_id = self._owner_id(user_id)
        row = AgentSessionRow(title=title, user_id=owner_id)
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
        image_version_ids: list[uuid.UUID] | None = None,
    ) -> AgentMessageRow:
        self._require_owned_session(session_id)
        linked_version_ids = self._valid_session_version_ids(
            session_id,
            image_version_ids
            if image_version_ids is not None
            else ([image_version_id] if image_version_id is not None else []),
        )
        linked_version_id = linked_version_ids[-1] if linked_version_ids else None

        row = AgentMessageRow(
            session_id=session_id,
            role=role,
            content=content,
            response_id=response_id,
            tool_call_id=tool_call_id,
            image_version_id=linked_version_id,
        )
        try:
            self.db.add(row)
            self.db.flush()
            for position, version_id in enumerate(linked_version_ids):
                self.db.add(
                    AgentMessageImageVersionRow(
                        message_id=row.id,
                        image_version_id=version_id,
                        position=position,
                    )
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(row)
        return row

    def list_sessions(
        self, user_id: uuid.UUID | None = None
    ) -> list[AgentSessionRow]:
        owner_id = self._owner_id(user_id)
        return list(
            self.db.scalars(
                select(AgentSessionRow)
                .where(AgentSessionRow.user_id == owner_id)
                .order_by(
                    AgentSessionRow.updated_at.desc(),
                    AgentSessionRow.created_at.desc(),
                    AgentSessionRow.id.desc(),
                )
            )
        )

    def update_session_summary(self, session_id: uuid.UUID, summary: str) -> None:
        session = self._get_owned_session(session_id)
        if session is None:
            return

        session.summary = summary
        session.summary_updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def update_session_title(self, session_id: uuid.UUID, title: str) -> None:
        session = self._get_owned_session(session_id)
        if session is None:
            return

        normalized = title.strip()
        if normalized:
            session.title = normalized[:120]
            self.db.commit()

    def touch_session(self, session_id: uuid.UUID) -> None:
        session = self._get_owned_session(session_id)
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
        self._require_owned_session(session_id)
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
        session = self._get_owned_session(session_id)
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
        session = self._get_owned_session(session_id)
        if session is None:
            return

        session.previous_response_id = response_id
        self.db.commit()

    def restore_version(self, session_id: uuid.UUID, version_id: uuid.UUID) -> None:
        session = self._get_owned_session(session_id)
        if session is None:
            return

        version = self._get_session_version(session_id, version_id)
        if version is None:
            return

        session.current_version_id = version.id
        self.db.commit()

    def remove_turn_artifacts(
        self,
        session_id: uuid.UUID,
        message_ids: list[uuid.UUID],
        version_ids: list[uuid.UUID],
        restored_current_version_id: uuid.UUID | None,
        restored_previous_response_id: str | None = None,
        restored_summary: str | None = None,
        restored_summary_updated_at: datetime | None = None,
    ) -> None:
        session = self._get_owned_session(session_id)
        if session is None:
            return

        if restored_current_version_id is not None:
            restored = self._get_session_version(session_id, restored_current_version_id)
            session.current_version_id = restored.id if restored is not None else None
        else:
            session.current_version_id = None
        session.previous_response_id = restored_previous_response_id
        session.summary = restored_summary
        session.summary_updated_at = restored_summary_updated_at

        if message_ids:
            self.db.query(AgentMessageImageVersionRow).filter(
                AgentMessageImageVersionRow.message_id.in_(message_ids),
            ).delete(synchronize_session=False)
            self.db.query(AgentMessageRow).filter(
                AgentMessageRow.session_id == session_id,
                AgentMessageRow.id.in_(message_ids),
            ).delete(synchronize_session=False)
        if version_ids:
            self.db.query(AgentMessageImageVersionRow).filter(
                AgentMessageImageVersionRow.image_version_id.in_(version_ids),
            ).delete(synchronize_session=False)
        if version_ids:
            self.db.query(ImageVersionRow).filter(
                ImageVersionRow.session_id == session_id,
                ImageVersionRow.id.in_(version_ids),
            ).delete(synchronize_session=False)
        self.db.commit()

    def delete_session(self, session_id: uuid.UUID) -> None:
        session = self._get_owned_session(session_id)
        if session is None:
            return

        message_ids = list(
            self.db.scalars(
                select(AgentMessageRow.id).where(
                    AgentMessageRow.session_id == session_id
                )
            )
        )
        version_ids = list(
            self.db.scalars(
                select(ImageVersionRow.id).where(
                    ImageVersionRow.session_id == session_id
                )
            )
        )
        if message_ids:
            self.db.query(AgentMessageImageVersionRow).filter(
                AgentMessageImageVersionRow.message_id.in_(message_ids),
            ).delete(synchronize_session=False)
        if version_ids:
            self.db.query(AgentMessageImageVersionRow).filter(
                AgentMessageImageVersionRow.image_version_id.in_(version_ids),
            ).delete(synchronize_session=False)
        self.db.query(AgentMessageRow).filter(
            AgentMessageRow.session_id == session_id
        ).delete(synchronize_session=False)
        self.db.query(ImageVersionRow).filter(
            ImageVersionRow.session_id == session_id
        ).delete(synchronize_session=False)
        self.db.delete(session)
        self.db.commit()

    def get_session_state(
        self, session_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> AgentSessionState | None:
        session = self._get_owned_session(session_id, user_id)
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
        message_image_versions = {
            message.id: []
            for message in messages
        }
        if messages:
            links = list(
                self.db.scalars(
                    select(AgentMessageImageVersionRow)
                    .where(
                        AgentMessageImageVersionRow.message_id.in_(
                            [message.id for message in messages]
                        )
                    )
                    .order_by(
                        AgentMessageImageVersionRow.message_id,
                        AgentMessageImageVersionRow.position,
                    )
                )
            )
            for link in links:
                message_image_versions.setdefault(link.message_id, []).append(
                    link.image_version_id
                )

        return AgentSessionState(
            session=session,
            messages=messages,
            versions=_order_versions_by_parent_chain(versions),
            message_image_versions=message_image_versions,
        )

    def _owner_id(self, user_id: uuid.UUID | None = None) -> uuid.UUID:
        owner_id = user_id if user_id is not None else self.user_id
        if owner_id is None:
            raise ValueError("AgentRepository requires a user_id.")
        return owner_id

    def _get_owned_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID | None = None
    ) -> AgentSessionRow | None:
        return self.db.scalar(
            select(AgentSessionRow).where(
                AgentSessionRow.id == session_id,
                AgentSessionRow.user_id == self._owner_id(user_id),
            )
        )

    def _require_owned_session(self, session_id: uuid.UUID) -> AgentSessionRow:
        session = self._get_owned_session(session_id)
        if session is None:
            raise ValueError("Conversation not found.")
        return session

    def _get_session_version(
        self, session_id: uuid.UUID, version_id: uuid.UUID
    ) -> ImageVersionRow | None:
        return self.db.scalar(
            select(ImageVersionRow).where(
                ImageVersionRow.id == version_id,
                ImageVersionRow.session_id == session_id,
            )
        )

    def _valid_session_version_ids(
        self, session_id: uuid.UUID, version_ids: list[uuid.UUID]
    ) -> list[uuid.UUID]:
        valid = []
        seen = set()
        for version_id in version_ids:
            if version_id in seen:
                continue
            seen.add(version_id)
            version = self._get_session_version(session_id, version_id)
            if version is not None:
                valid.append(version.id)
        return valid


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
