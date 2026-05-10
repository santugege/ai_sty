from __future__ import annotations

import re

from app.account_repository import AccountRepository
from app.auth_schemas import UserDto
from app.auth_security import hash_password, verify_password
from app.user_models import UserRow

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


class AccountServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AccountService:
    def __init__(self, repository: AccountRepository) -> None:
        self.repository = repository

    def register(self, email: str, username: str, password: str) -> UserRow:
        normalized_email = _normalize_email(email)
        normalized_username = _normalize_username(username)
        _validate_email(normalized_email)
        _validate_username(normalized_username)
        _validate_password(password)

        if self.repository.get_by_email(normalized_email) is not None:
            raise AccountServiceError("邮箱已被注册")
        if self.repository.get_by_username(normalized_username) is not None:
            raise AccountServiceError("用户名已被注册")

        return self.repository.create_user(
            email=normalized_email,
            username=normalized_username,
            password_hash=hash_password(password),
            is_admin=not self.repository.has_users(),
            retry_as_regular_on_admin_conflict=True,
        )

    def login(self, email: str, password: str) -> UserRow:
        user = self.repository.get_by_email(_normalize_email(email))
        if user is None or not verify_password(password, user.password_hash):
            raise AccountServiceError("邮箱或密码错误", status_code=401)
        if not user.is_active:
            raise AccountServiceError("账号已停用", status_code=403)
        return user

    def list_users(self) -> list[UserRow]:
        return self.repository.list_users()

    def update_user(
        self,
        user_id: str,
        email: str | None = None,
        username: str | None = None,
        is_active: bool | None = None,
        acting_user: UserRow | None = None,
    ) -> UserRow:
        user = self._require_user(user_id)

        if email is not None:
            normalized_email = _normalize_email(email)
            _validate_email(normalized_email)
            existing = self.repository.get_by_email(normalized_email)
            if existing is not None and existing.id != user.id:
                raise AccountServiceError("邮箱已被注册")
            user.email = normalized_email

        if username is not None:
            normalized_username = _normalize_username(username)
            _validate_username(normalized_username)
            existing = self.repository.get_by_username(normalized_username)
            if existing is not None and existing.id != user.id:
                raise AccountServiceError("用户名已被注册")
            user.username = normalized_username

        if is_active is not None:
            if acting_user is not None and acting_user.id == user.id and not is_active:
                raise AccountServiceError("不能停用当前管理员账号")
            user.is_active = is_active

        return self.repository.save(user)

    def reset_password(self, user_id: str, password: str) -> UserRow:
        _validate_password(password)
        user = self._require_user(user_id)
        user.password_hash = hash_password(password)
        return self.repository.save(user)

    def _require_user(self, user_id: str) -> UserRow:
        user = self.repository.get_by_user_id(user_id)
        if user is None:
            raise AccountServiceError("用户不存在", status_code=404)
        return user


def user_to_dto(user: UserRow) -> UserDto:
    return UserDto(
        id=str(user.id),
        userId=user.user_id,
        email=user.email,
        username=user.username,
        isAdmin=user.is_admin,
        isActive=user.is_active,
        createdAt=user.created_at.isoformat(),
        updatedAt=user.updated_at.isoformat(),
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_username(username: str) -> str:
    return username.strip()


def _validate_email(email: str) -> None:
    if not EMAIL_RE.match(email):
        raise AccountServiceError("请输入有效邮箱")


def _validate_username(username: str) -> None:
    if len(username) < 2:
        raise AccountServiceError("用户名至少需要 2 个字符")


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountServiceError("密码至少需要 8 个字符")
