import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.account_repository import AccountRepository
from app.account_service import AccountService, AccountServiceError
from app.db import Base


def make_service() -> AccountService:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    return AccountService(AccountRepository(session))


def test_first_registered_user_becomes_admin():
    service = make_service()

    user = service.register(
        email="owner@example.com",
        username="owner",
        password="password123",
    )

    assert user.email == "owner@example.com"
    assert user.username == "owner"
    assert user.is_admin is True
    assert user.is_active is True
    assert user.user_id.startswith("U")


def test_second_registered_user_is_not_admin():
    service = make_service()

    service.register("owner@example.com", "owner", "password123")
    user = service.register("user@example.com", "user", "password123")

    assert user.is_admin is False


def test_register_rejects_duplicate_email_and_username():
    service = make_service()
    service.register("owner@example.com", "owner", "password123")

    with pytest.raises(AccountServiceError, match="邮箱已被注册"):
        service.register("owner@example.com", "other", "password123")

    with pytest.raises(AccountServiceError, match="用户名已被注册"):
        service.register("other@example.com", "owner", "password123")


def test_login_verifies_password_and_active_status():
    service = make_service()
    user = service.register("owner@example.com", "owner", "password123")

    assert service.login("owner@example.com", "password123").id == user.id

    with pytest.raises(AccountServiceError, match="邮箱或密码错误"):
        service.login("owner@example.com", "wrong-password")

    service.update_user(user.user_id, is_active=False)
    with pytest.raises(AccountServiceError, match="账号已停用"):
        service.login("owner@example.com", "password123")


def test_admin_update_does_not_accept_admin_promotion():
    service = make_service()
    service.register("owner@example.com", "owner", "password123")
    user = service.register("user@example.com", "user", "password123")

    updated = service.update_user(
        user.user_id,
        email="renamed@example.com",
        username="renamed",
        is_active=False,
    )

    assert updated.email == "renamed@example.com"
    assert updated.username == "renamed"
    assert updated.is_active is False
    assert updated.is_admin is False


def test_admin_cannot_deactivate_self():
    service = make_service()
    owner = service.register("owner@example.com", "owner", "password123")

    with pytest.raises(AccountServiceError, match="不能停用当前管理员账号"):
        service.update_user(owner.user_id, is_active=False, acting_user=owner)


def test_reset_password_changes_login_password():
    service = make_service()
    service.register("owner@example.com", "owner", "password123")
    user = service.register("user@example.com", "user", "password123")

    service.reset_password(user.user_id, "new-password123")

    assert service.login("user@example.com", "new-password123").id == user.id
    with pytest.raises(AccountServiceError):
        service.login("user@example.com", "password123")
