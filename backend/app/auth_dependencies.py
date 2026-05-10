from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.account_repository import AccountRepository
from app.auth_security import SESSION_COOKIE_NAME, read_session_token
from app.db import get_db_session
from app.user_models import UserRow


def get_optional_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db_session),
) -> UserRow | None:
    if not session_token:
        return None
    internal_id = read_session_token(session_token)
    if internal_id is None:
        return None
    user = AccountRepository(db).get_by_id(internal_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    current_user: UserRow | None = Depends(get_optional_current_user),
) -> UserRow:
    if current_user is None:
        raise HTTPException(status_code=401, detail="请先登录。")
    return current_user


def require_admin_user(current_user: UserRow = Depends(get_current_user)) -> UserRow:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限。")
    return current_user
