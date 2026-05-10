from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_security import generate_user_id
from app.user_models import UserRow


class AccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def has_users(self) -> bool:
        return self.db.scalar(select(func.count(UserRow.id))) > 0

    def next_user_id(self) -> str:
        for _ in range(10):
            user_id = generate_user_id()
            if self.get_by_user_id(user_id) is None:
                return user_id
        raise RuntimeError("Could not allocate a unique user id.")

    def create_user(
        self,
        email: str,
        username: str,
        password_hash: str,
        is_admin: bool,
        retry_as_regular_on_admin_conflict: bool = False,
    ) -> UserRow:
        for _ in range(10):
            row = UserRow(
                user_id=self.next_user_id(),
                email=email,
                username=username,
                password_hash=password_hash,
                is_admin=is_admin,
                is_active=True,
            )
            try:
                self.db.add(row)
                self.db.commit()
                self.db.refresh(row)
                return row
            except IntegrityError as error:
                self.db.rollback()
                conflict = _integrity_conflict(error)
                if conflict == "admin" and is_admin and retry_as_regular_on_admin_conflict:
                    is_admin = False
                    continue
                if conflict == "user_id":
                    continue
                raise _service_error_for_conflict(conflict) from error

        raise RuntimeError("Could not allocate a unique user id.")

    def get_by_id(self, user_id: uuid.UUID | str) -> UserRow | None:
        try:
            internal_id = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(user_id)
        except ValueError:
            return None
        return self.db.get(UserRow, internal_id)

    def get_by_user_id(self, user_id: str) -> UserRow | None:
        return self.db.scalar(select(UserRow).where(UserRow.user_id == user_id))

    def get_by_email(self, email: str) -> UserRow | None:
        return self.db.scalar(select(UserRow).where(UserRow.email == email))

    def get_by_username(self, username: str) -> UserRow | None:
        return self.db.scalar(select(UserRow).where(UserRow.username == username))

    def list_users(self) -> list[UserRow]:
        return list(
            self.db.scalars(
                select(UserRow).order_by(
                    UserRow.is_admin.desc(),
                    UserRow.created_at.asc(),
                    UserRow.id.asc(),
                )
            )
        )

    def save(self, user: UserRow) -> UserRow:
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as error:
            self.db.rollback()
            raise _service_error_for_conflict(_integrity_conflict(error)) from error


def _integrity_conflict(error: IntegrityError) -> str:
    message = str(error.orig).lower()
    if "users.email" in message or "ix_users_email" in message:
        return "email"
    if "users.username" in message or "ix_users_username" in message:
        return "username"
    if "users.user_id" in message or "ix_users_user_id" in message:
        return "user_id"
    if "ix_users_single_admin" in message or "users.is_admin" in message:
        return "admin"
    return "unknown"


def _service_error_for_conflict(conflict: str) -> Exception:
    from app.account_service import AccountServiceError

    if conflict == "email":
        return AccountServiceError("邮箱已被注册")
    if conflict == "username":
        return AccountServiceError("用户名已被注册")
    if conflict == "admin":
        return AccountServiceError("管理员账号已存在")
    return AccountServiceError("账号保存失败")
