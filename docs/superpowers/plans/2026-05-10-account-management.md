# Account Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add simple email/username/password accounts, make the first registered user the only administrator, require login for app features, and add administrator-only account management.

**Architecture:** Add a `users` table and a small auth layer around signed HTTP-only cookies. Keep permissions to `is_admin` and `is_active`; no role tables and no admin promotion endpoint. Frontend auth state is loaded through `/api/auth/me`, with public login/register pages and a protected app shell.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, bcrypt, PostgreSQL/SQLite tests, Next.js App Router, React client components, Node source tests.

---

## File Structure

Backend:

- Create `backend/app/user_models.py`: SQLAlchemy `UserRow` model and `utc_now`.
- Create `backend/alembic/versions/20260510_0004_users.py`: users table migration.
- Modify `backend/alembic/env.py`: import `app.user_models` so Alembic sees the table.
- Modify `backend/requirements.txt`: add `bcrypt`.
- Modify `backend/.env.example`: add session settings.
- Create `backend/app/auth_schemas.py`: request/response DTOs.
- Create `backend/app/auth_security.py`: password hashing, user id generation, signed session token helpers.
- Create `backend/app/account_repository.py`: database account persistence.
- Create `backend/app/account_service.py`: registration, login, admin update, and reset-password rules.
- Create `backend/app/auth_dependencies.py`: current-user and admin dependencies.
- Modify `backend/app/main.py`: auth routes, admin routes, HTTP error JSON handler, and route protection.
- Create `backend/tests/test_user_models.py`: table and migration shape tests.
- Create `backend/tests/test_auth_security.py`: password and session token tests.
- Create `backend/tests/test_account_service.py`: first-admin and account-management service tests.
- Create `backend/tests/test_auth_routes.py`: public auth, admin routes, and protected route tests.
- Modify existing route tests in `backend/tests/test_agent_routes.py` and `backend/tests/test_main.py`: authenticate requests that now require login.

Frontend:

- Create `frontend/src/lib/auth-api.ts`: auth and admin API client.
- Modify `frontend/src/lib/agent-api.ts`: include cookies and read `detail` errors.
- Modify `frontend/src/lib/image-api.ts`: include cookies and read `detail` errors.
- Create `frontend/src/components/auth-provider.tsx`: current user context and route guard.
- Create `frontend/src/components/app-nav.tsx`: shared navigation with admin-only account link and logout.
- Create `frontend/src/app/login/page.tsx`: login page.
- Create `frontend/src/app/register/page.tsx`: registration page.
- Create `frontend/src/app/admin/accounts/page.tsx`: admin account management page.
- Modify `frontend/src/app/layout.tsx`: wrap children in `AuthProvider`.
- Modify `frontend/src/app/page.tsx`: use shared navigation.
- Modify `frontend/src/app/agent/page.tsx` or `frontend/src/components/agent-image-workbench.tsx`: surface logout/account navigation if needed.
- Create or modify frontend tests for auth API, auth pages, admin source, and authenticated fetch options.

---

### Task 1: User Table And Migration

**Files:**
- Create: `backend/app/user_models.py`
- Create: `backend/alembic/versions/20260510_0004_users.py`
- Modify: `backend/alembic/env.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_user_models.py`

- [ ] **Step 1: Write failing user model tests**

Create `backend/tests/test_user_models.py`:

```python
from pathlib import Path

from app.db import Base
from app.user_models import UserRow


def test_base_metadata_includes_users_table():
    assert "users" in set(Base.metadata.tables)


def test_user_columns_match_account_design():
    assert {
        "id",
        "user_id",
        "email",
        "username",
        "password_hash",
        "is_admin",
        "is_active",
        "created_at",
        "updated_at",
    } <= set(UserRow.__table__.columns.keys())


def test_user_unique_constraints_are_declared():
    columns = UserRow.__table__.columns

    assert columns["user_id"].unique is True
    assert columns["email"].unique is True
    assert columns["username"].unique is True


def test_users_migration_exists_and_does_not_allow_admin_promotion_fields():
    migration = Path(
        "backend/alembic/versions/20260510_0004_users.py"
    ).read_text(encoding="utf-8")

    assert 'op.create_table("users"' in migration
    assert '"user_id"' in migration
    assert '"is_admin"' in migration
    assert "roles" not in migration
    assert "permissions" not in migration
```

- [ ] **Step 2: Run user model tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_user_models.py -q
```

Expected: FAIL because `app.user_models` and the migration do not exist yet.

- [ ] **Step 3: Add bcrypt dependency and session env examples**

Add this line to `backend/requirements.txt`:

```txt
bcrypt
```

Append to `backend/.env.example`:

```env
SESSION_SECRET=change-me-in-production
SESSION_TTL_HOURS=24
SESSION_COOKIE_SECURE=false
```

- [ ] **Step 4: Create the user model**

Create `backend/app/user_models.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
```

- [ ] **Step 5: Import the model in Alembic env**

In `backend/alembic/env.py`, add the import next to the existing model import:

```python
from app import agent_models, user_models  # noqa: F401
```

- [ ] **Step 6: Add the users migration**

Create `backend/alembic/versions/20260510_0004_users.py`:

```python
"""create users table

Revision ID: 20260510_0004
Revises: 20260510_0003
Create Date: 2026-05-10 00:04:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0004"
down_revision = "20260510_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_user_id", "users", ["user_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_user_id", table_name="users")
    op.drop_table("users")
```

- [ ] **Step 7: Run user model tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_user_models.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
rtk git add backend/requirements.txt backend/.env.example backend/app/user_models.py backend/alembic/env.py backend/alembic/versions/20260510_0004_users.py backend/tests/test_user_models.py
rtk git commit -m "feat: add users table"
```

---

### Task 2: Auth Security And Account Service

**Files:**
- Create: `backend/app/auth_schemas.py`
- Create: `backend/app/auth_security.py`
- Create: `backend/app/account_repository.py`
- Create: `backend/app/account_service.py`
- Test: `backend/tests/test_auth_security.py`
- Test: `backend/tests/test_account_service.py`

- [ ] **Step 1: Write failing auth security tests**

Create `backend/tests/test_auth_security.py`:

```python
from datetime import datetime, timedelta, timezone

from app.auth_security import (
    generate_user_id,
    hash_password,
    make_session_token,
    read_session_token,
    verify_password,
)


def test_hash_password_does_not_store_plaintext_and_verifies():
    password_hash = hash_password("strong-password")

    assert password_hash != "strong-password"
    assert verify_password("strong-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_generate_user_id_is_business_readable():
    user_id = generate_user_id()

    assert user_id.startswith("U")
    assert len(user_id) == 9


def test_signed_session_token_round_trips_user_id(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    token = make_session_token("00000000-0000-0000-0000-000000000001", expires_at)

    assert read_session_token(token) == "00000000-0000-0000-0000-000000000001"


def test_expired_session_token_returns_none(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    token = make_session_token("00000000-0000-0000-0000-000000000001", expires_at)

    assert read_session_token(token) is None


def test_tampered_session_token_returns_none(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    token = make_session_token("00000000-0000-0000-0000-000000000001", expires_at)

    assert read_session_token(token + "x") is None
```

- [ ] **Step 2: Write failing account service tests**

Create `backend/tests/test_account_service.py`:

```python
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
```

- [ ] **Step 3: Run service tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_auth_security.py backend/tests/test_account_service.py -q
```

Expected: FAIL because auth modules do not exist.

- [ ] **Step 4: Create auth DTOs**

Create `backend/app/auth_schemas.py`:

```python
from __future__ import annotations

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AdminUserUpdateRequest(BaseModel):
    email: str | None = None
    username: str | None = None
    isActive: bool | None = None


class AdminPasswordResetRequest(BaseModel):
    password: str


class UserDto(BaseModel):
    id: str
    userId: str
    email: str
    username: str
    isAdmin: bool
    isActive: bool
    createdAt: str
    updatedAt: str


class AuthEnvelope(BaseModel):
    user: UserDto | None


class UserListEnvelope(BaseModel):
    users: list[UserDto]
```

- [ ] **Step 5: Create password, user id, and session helpers**

Create `backend/app/auth_security.py`:

```python
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

SESSION_COOKIE_NAME = "ai_sty_session"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_user_id() -> str:
    return f"U{secrets.token_hex(4).upper()}"


def session_ttl_hours() -> int:
    try:
        return max(1, int(os.getenv("SESSION_TTL_HOURS", "24")))
    except ValueError:
        return 24


def session_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=session_ttl_hours())


def session_cookie_secure() -> bool:
    return os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


def make_session_token(user_internal_id: str, expires_at: datetime | None = None) -> str:
    expires = expires_at or session_expires_at()
    payload = {
        "sub": user_internal_id,
        "exp": int(expires.timestamp()),
    }
    body = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = _signature(body)
    return f"{body}.{signature}"


def read_session_token(token: str) -> str | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None

    expected = _signature(body)
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    expires_at = int(payload.get("exp", 0))
    if expires_at <= int(datetime.now(timezone.utc).timestamp()):
        return None

    subject = payload.get("sub")
    return subject if isinstance(subject, str) and subject else None


def _session_secret() -> bytes:
    return os.getenv("SESSION_SECRET", "dev-insecure-session-secret").encode("utf-8")


def _signature(body: str) -> str:
    digest = hmac.new(_session_secret(), body.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
```

- [ ] **Step 6: Create account repository**

Create `backend/app/account_repository.py`:

```python
from __future__ import annotations

import uuid

from sqlalchemy import func, select
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
    ) -> UserRow:
        row = UserRow(
            user_id=self.next_user_id(),
            email=email,
            username=username,
            password_hash=password_hash,
            is_admin=is_admin,
            is_active=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_id(self, user_id: uuid.UUID | str) -> UserRow | None:
        try:
            internal_id = uuid.UUID(str(user_id))
        except ValueError:
            return None
        return self.db.get(UserRow, internal_id)

    def get_by_user_id(self, user_id: str) -> UserRow | None:
        return self.db.scalar(select(UserRow).where(UserRow.user_id == user_id))

    def get_by_email(self, email: str) -> UserRow | None:
        return self.db.scalar(select(UserRow).where(UserRow.email == email.lower()))

    def get_by_username(self, username: str) -> UserRow | None:
        return self.db.scalar(select(UserRow).where(UserRow.username == username))

    def list_users(self) -> list[UserRow]:
        return list(
            self.db.scalars(select(UserRow).order_by(UserRow.created_at.asc(), UserRow.id.asc()))
        )

    def save(self, user: UserRow) -> UserRow:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
```

- [ ] **Step 7: Create account service**

Create `backend/app/account_service.py`:

```python
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
        self.status_code = status_code


class AccountService:
    def __init__(self, repo: AccountRepository) -> None:
        self.repo = repo

    def register(self, email: str, username: str, password: str) -> UserRow:
        normalized_email = _normalize_email(email)
        normalized_username = _normalize_username(username)
        _validate_email(normalized_email)
        _validate_username(normalized_username)
        _validate_password(password)

        if self.repo.get_by_email(normalized_email) is not None:
            raise AccountServiceError("邮箱已被注册。")
        if self.repo.get_by_username(normalized_username) is not None:
            raise AccountServiceError("用户名已被注册。")

        is_admin = not self.repo.has_users()
        return self.repo.create_user(
            email=normalized_email,
            username=normalized_username,
            password_hash=hash_password(password),
            is_admin=is_admin,
        )

    def login(self, email: str, password: str) -> UserRow:
        user = self.repo.get_by_email(_normalize_email(email))
        if user is None or not verify_password(password, user.password_hash):
            raise AccountServiceError("邮箱或密码错误。", status_code=401)
        if not user.is_active:
            raise AccountServiceError("账号已停用。", status_code=403)
        return user

    def list_users(self) -> list[UserRow]:
        return self.repo.list_users()

    def update_user(
        self,
        user_id: str,
        email: str | None = None,
        username: str | None = None,
        is_active: bool | None = None,
        acting_user: UserRow | None = None,
    ) -> UserRow:
        user = self.repo.get_by_user_id(user_id)
        if user is None:
            raise AccountServiceError("账号不存在。", status_code=404)

        if email is not None:
            normalized_email = _normalize_email(email)
            _validate_email(normalized_email)
            existing = self.repo.get_by_email(normalized_email)
            if existing is not None and existing.id != user.id:
                raise AccountServiceError("邮箱已被注册。")
            user.email = normalized_email

        if username is not None:
            normalized_username = _normalize_username(username)
            _validate_username(normalized_username)
            existing = self.repo.get_by_username(normalized_username)
            if existing is not None and existing.id != user.id:
                raise AccountServiceError("用户名已被注册。")
            user.username = normalized_username

        if is_active is not None:
            if acting_user is not None and acting_user.id == user.id and is_active is False:
                raise AccountServiceError("不能停用当前管理员账号。")
            user.is_active = is_active

        return self.repo.save(user)

    def reset_password(self, user_id: str, password: str) -> UserRow:
        _validate_password(password)
        user = self.repo.get_by_user_id(user_id)
        if user is None:
            raise AccountServiceError("账号不存在。", status_code=404)
        user.password_hash = hash_password(password)
        return self.repo.save(user)


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
        raise AccountServiceError("请输入有效邮箱。")


def _validate_username(username: str) -> None:
    if not username:
        raise AccountServiceError("请输入用户名。")


def _validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AccountServiceError("密码至少需要 8 位。")
```

- [ ] **Step 8: Run auth service tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_auth_security.py backend/tests/test_account_service.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
rtk git add backend/app/auth_schemas.py backend/app/auth_security.py backend/app/account_repository.py backend/app/account_service.py backend/tests/test_auth_security.py backend/tests/test_account_service.py
rtk git commit -m "feat: add account auth service"
```

---

### Task 3: Auth Routes And Admin Routes

**Files:**
- Create: `backend/app/auth_dependencies.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth_routes.py`

- [ ] **Step 1: Write failing auth route tests**

Create `backend/tests/test_auth_routes.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.auth_security import SESSION_COOKIE_NAME
from app.db import Base, get_db_session
from app.main import app


def make_client():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    def override():
        yield session

    app.dependency_overrides[get_db_session] = override
    return TestClient(app), session


def cleanup_overrides():
    app.dependency_overrides.pop(get_db_session, None)


def test_register_first_user_sets_admin_cookie_and_returns_user():
    client, _ = make_client()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert response.json()["user"]["isAdmin"] is True
    assert response.json()["user"]["userId"].startswith("U")
    assert SESSION_COOKIE_NAME in response.cookies


def test_login_logout_and_me_flow():
    client, _ = make_client()
    try:
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
        client.post("/api/auth/logout")
        assert client.get("/api/auth/me").json() == {"user": None}

        login = client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        me = client.get("/api/auth/me")
    finally:
        cleanup_overrides()

    assert login.status_code == 200
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "owner@example.com"


def test_admin_users_rejects_regular_user_and_allows_admin():
    client, _ = make_client()
    try:
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "username": "user",
                "password": "password123",
            },
        )
        regular_response = client.get("/api/admin/users")
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        admin_response = client.get("/api/admin/users")
    finally:
        cleanup_overrides()

    assert regular_response.status_code == 403
    assert admin_response.status_code == 200
    assert [item["email"] for item in admin_response.json()["users"]] == [
        "owner@example.com",
        "user@example.com",
    ]


def test_admin_update_does_not_accept_is_admin_promotion():
    client, _ = make_client()
    try:
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
        client.post("/api/auth/logout")
        user_response = client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "username": "user",
                "password": "password123",
            },
        )
        user_id = user_response.json()["user"]["userId"]
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        response = client.patch(
            f"/api/admin/users/{user_id}",
            json={
                "email": "renamed@example.com",
                "username": "renamed",
                "isActive": False,
                "isAdmin": True,
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "renamed@example.com"
    assert response.json()["user"]["username"] == "renamed"
    assert response.json()["user"]["isActive"] is False
    assert response.json()["user"]["isAdmin"] is False


def test_admin_password_reset_changes_user_password():
    client, _ = make_client()
    try:
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
        client.post("/api/auth/logout")
        user_response = client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "username": "user",
                "password": "password123",
            },
        )
        user_id = user_response.json()["user"]["userId"]
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        reset_response = client.post(
            f"/api/admin/users/{user_id}/password",
            json={"password": "new-password123"},
        )
        client.post("/api/auth/logout")
        login_response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "new-password123"},
        )
    finally:
        cleanup_overrides()

    assert reset_response.status_code == 200
    assert login_response.status_code == 200
```

- [ ] **Step 2: Run auth route tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_auth_routes.py -q
```

Expected: FAIL because routes and dependencies do not exist.

- [ ] **Step 3: Create auth dependencies**

Create `backend/app/auth_dependencies.py`:

```python
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
```

- [ ] **Step 4: Add auth helpers and routes to main.py**

In `backend/app/main.py`, add imports:

```python
from fastapi import HTTPException, Request, Response

from app.account_repository import AccountRepository
from app.account_service import AccountService, AccountServiceError, user_to_dto
from app.auth_dependencies import (
    get_current_user,
    get_optional_current_user,
    require_admin_user,
)
from app.auth_schemas import (
    AdminPasswordResetRequest,
    AdminUserUpdateRequest,
    AuthEnvelope,
    LoginRequest,
    RegisterRequest,
    UserListEnvelope,
)
from app.auth_security import (
    SESSION_COOKIE_NAME,
    make_session_token,
    session_cookie_secure,
    session_expires_at,
)
from app.user_models import UserRow
```

Add this exception handler after middleware setup:

```python
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, error: HTTPException):
    return JSONResponse({"error": error.detail}, status_code=error.status_code)
```

Add helper functions before the route definitions:

```python
def build_account_service(db: Session) -> AccountService:
    return AccountService(AccountRepository(db))


def set_session_cookie(response: Response, user: UserRow) -> None:
    expires_at = session_expires_at()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=make_session_token(str(user.id), expires_at),
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
        expires=expires_at,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
    )


def auth_error_response(error: AccountServiceError) -> JSONResponse:
    return JSONResponse({"error": str(error)}, status_code=error.status_code)
```

Add these public and admin routes before the existing app feature routes:

```python
@app.post("/api/auth/register")
async def register_account(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db_session),
):
    try:
        user = build_account_service(db).register(
            email=payload.email,
            username=payload.username,
            password=payload.password,
        )
        set_session_cookie(response, user)
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/auth/login")
async def login_account(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db_session),
):
    try:
        user = build_account_service(db).login(payload.email, payload.password)
        set_session_cookie(response, user)
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/auth/logout")
async def logout_account(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me")
async def get_auth_user(
    current_user: UserRow | None = Depends(get_optional_current_user),
):
    return AuthEnvelope(
        user=user_to_dto(current_user) if current_user is not None else None
    ).model_dump(mode="json")


@app.get("/api/admin/users")
async def list_users(
    db: Session = Depends(get_db_session),
    admin_user: UserRow = Depends(require_admin_user),
):
    users = build_account_service(db).list_users()
    return UserListEnvelope(users=[user_to_dto(user) for user in users]).model_dump(
        mode="json"
    )


@app.patch("/api/admin/users/{user_id}")
async def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    db: Session = Depends(get_db_session),
    admin_user: UserRow = Depends(require_admin_user),
):
    try:
        user = build_account_service(db).update_user(
            user_id,
            email=payload.email,
            username=payload.username,
            is_active=payload.isActive,
            acting_user=admin_user,
        )
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)


@app.post("/api/admin/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    payload: AdminPasswordResetRequest,
    db: Session = Depends(get_db_session),
    admin_user: UserRow = Depends(require_admin_user),
):
    try:
        user = build_account_service(db).reset_password(user_id, payload.password)
        return AuthEnvelope(user=user_to_dto(user)).model_dump(mode="json")
    except AccountServiceError as error:
        return auth_error_response(error)
```

- [ ] **Step 5: Run auth route tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_auth_routes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add backend/app/auth_dependencies.py backend/app/main.py backend/tests/test_auth_routes.py
rtk git commit -m "feat: add auth and account admin routes"
```

---

### Task 4: Protect Existing Backend Features

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_agent_routes.py`
- Modify: `backend/tests/test_main.py`
- Test: `backend/tests/test_auth_routes.py`

- [ ] **Step 1: Add failing protected-route tests**

Append to `backend/tests/test_auth_routes.py`:

```python
def test_image_generation_requires_login():
    client, _ = make_client()
    try:
        response = client.post(
            "/api/images/generate",
            data={"toolId": "product", "prompt": "商品图", "size": "1536x1024"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}


def test_agent_sessions_require_login():
    client, _ = make_client()
    try:
        response = client.get("/api/agent/sessions")
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}
```

- [ ] **Step 2: Run protected-route tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_auth_routes.py::test_image_generation_requires_login backend/tests/test_auth_routes.py::test_agent_sessions_require_login -q
```

Expected: FAIL because existing feature routes are still public.

- [ ] **Step 3: Require current user on app feature routes**

In `backend/app/main.py`, add this dependency parameter to each feature route:

```python
current_user: UserRow = Depends(get_current_user),
```

Apply it to these route functions:

- `send_conversation_message`
- `reset_conversation`
- `list_agent_sessions`
- `create_agent_session`
- `get_agent_session`
- `send_agent_session_message`
- `generate_image`

For example:

```python
@app.get("/api/agent/sessions")
async def list_agent_sessions(
    db: Session = Depends(get_db_session),
    current_user: UserRow = Depends(get_current_user),
):
    try:
        envelope = build_agent_service(db).list_sessions()
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)
```

- [ ] **Step 4: Update existing backend route tests to authenticate**

In `backend/tests/test_agent_routes.py`, import the auth dependency:

```python
from app.auth_dependencies import get_current_user
from app.user_models import UserRow
```

Add helper functions:

```python
def override_current_user():
    return UserRow(
        email="tester@example.com",
        username="tester",
        password_hash="hash",
        user_id="U00000001",
        is_admin=True,
        is_active=True,
    )


def allow_authenticated_user():
    app.dependency_overrides[get_current_user] = override_current_user


def cleanup_auth_override():
    app.dependency_overrides.pop(get_current_user, None)
```

Wrap route tests that call protected routes with:

```python
allow_authenticated_user()
try:
    response = client.get("/api/agent/sessions")
finally:
    cleanup_auth_override()
```

Do the same in `backend/tests/test_main.py` for tests that call `POST /api/images/generate`.

- [ ] **Step 5: Run route tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_auth_routes.py backend/tests/test_agent_routes.py backend/tests/test_main.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
rtk git add backend/app/main.py backend/tests/test_auth_routes.py backend/tests/test_agent_routes.py backend/tests/test_main.py
rtk git commit -m "feat: require login for app features"
```

---

### Task 5: Frontend Auth API And Route Guard

**Files:**
- Create: `frontend/src/lib/auth-api.ts`
- Modify: `frontend/src/lib/agent-api.ts`
- Modify: `frontend/src/lib/image-api.ts`
- Create: `frontend/src/components/auth-provider.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Test: `frontend/tests/auth-flow.test.mjs`
- Modify: `frontend/tests/agent-workbench.test.mjs`

- [ ] **Step 1: Write failing frontend auth API tests**

Create `frontend/tests/auth-flow.test.mjs`:

```javascript
import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";
import ts from "typescript";

async function importTsModule(path) {
  const source = readFileSync(path, "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  });
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}#${Date.now()}-${Math.random()}`;
  return import(moduleUrl);
}

test("auth api client exposes account flow and uses cookie credentials", () => {
  const source = readFileSync("src/lib/auth-api.ts", "utf8");

  assert.match(source, /loginAccount/);
  assert.match(source, /registerAccount/);
  assert.match(source, /logoutAccount/);
  assert.match(source, /getCurrentUser/);
  assert.match(source, /listUsers/);
  assert.match(source, /updateUser/);
  assert.match(source, /resetUserPassword/);
  assert.match(source, /credentials: "include"/);
  assert.doesNotMatch(source, /isAdmin.*payload/);
});

test("auth api returns current user envelopes", async (t) => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), method: init?.method, credentials: init?.credentials });
    return new Response(
      JSON.stringify({
        user: {
          id: "uuid",
          userId: "U00000001",
          email: "owner@example.com",
          username: "owner",
          isAdmin: true,
          isActive: true,
          createdAt: "2026-05-10T00:00:00Z",
          updatedAt: "2026-05-10T00:00:00Z",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };

  const { getCurrentUser } = await importTsModule("src/lib/auth-api.ts");
  const envelope = await getCurrentUser();

  assert.equal(envelope.user.userId, "U00000001");
  assert.deepEqual(calls, [
    {
      url: "http://localhost:8000/api/auth/me",
      method: "GET",
      credentials: "include",
    },
  ]);
});

test("existing api clients send cookies and read detail errors", () => {
  const agentSource = readFileSync("src/lib/agent-api.ts", "utf8");
  const imageSource = readFileSync("src/lib/image-api.ts", "utf8");

  assert.match(agentSource, /credentials: "include"/);
  assert.match(agentSource, /payload\.detail/);
  assert.match(imageSource, /credentials: "include"/);
  assert.match(imageSource, /payload\.detail/);
});

test("auth provider protects private routes and leaves login register public", () => {
  const source = readFileSync("src/components/auth-provider.tsx", "utf8");

  assert.match(source, /publicPaths/);
  assert.match(source, /\/login/);
  assert.match(source, /\/register/);
  assert.match(source, /router\.replace/);
  assert.match(source, /AuthContext/);
});
```

- [ ] **Step 2: Run frontend auth tests red**

Run:

```bash
cd frontend
rtk npm test -- auth-flow
```

Expected: FAIL because auth frontend files do not exist.

- [ ] **Step 3: Create auth API client**

Create `frontend/src/lib/auth-api.ts`:

```typescript
const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type CurrentUser = {
  id: string;
  userId: string;
  email: string;
  username: string;
  isAdmin: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
};

export type AuthEnvelope = {
  user: CurrentUser | null;
  error?: string | null;
  detail?: string | null;
};

export type UserListEnvelope = {
  users: CurrentUser[];
};

export async function getCurrentUser(): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/auth/me`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function registerAccount(payload: {
  email: string;
  username: string;
  password: string;
}): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function loginAccount(payload: {
  email: string;
  password: string;
}): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function logoutAccount() {
  return readJsonResponse<{ ok: boolean }>(
    await fetch(`${apiBaseUrl}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    }),
  );
}

export async function listUsers(): Promise<UserListEnvelope> {
  return readJsonResponse<UserListEnvelope>(
    await fetch(`${apiBaseUrl}/api/admin/users`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function updateUser(
  userId: string,
  payload: { email?: string; username?: string; isActive?: boolean },
): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/admin/users/${encodeURIComponent(userId)}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function resetUserPassword(
  userId: string,
  password: string,
): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(
      `${apiBaseUrl}/api/admin/users/${encodeURIComponent(userId)}/password`,
      {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ password }),
      },
    ),
  );
}

async function readJsonResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & {
    error?: string | null;
    detail?: string | null;
  };
  if (!response.ok || payload.error || payload.detail) {
    throw new Error(payload.error || payload.detail || "请求失败。");
  }
  return payload;
}
```

- [ ] **Step 4: Update existing API clients for cookie sessions**

In every `fetch` call in `frontend/src/lib/agent-api.ts`, add:

```typescript
credentials: "include",
```

Update its error reader:

```typescript
const payload = (await response.json()) as T & {
  error?: string | null;
  detail?: string | null;
};
if (!response.ok || payload.error || payload.detail) {
  throw new Error(payload.error || payload.detail || "Agent request failed.");
}
```

In `frontend/src/lib/image-api.ts`, add `credentials: "include"` to the generation fetch and update `ImageGenerationPayload`:

```typescript
type ImageGenerationPayload = {
  image?: GeneratedImage;
  error?: string;
  detail?: string;
};
```

Change the thrown error to:

```typescript
throw new Error(payload.error || payload.detail || genericErrorMessage);
```

- [ ] **Step 5: Create auth provider and route guard**

Create `frontend/src/components/auth-provider.tsx`:

```tsx
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  getCurrentUser,
  logoutAccount,
  type CurrentUser,
} from "@/lib/auth-api";

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  refreshUser: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const publicPaths = ["/login", "/register"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const isPublicPath = publicPaths.includes(pathname);

  const refreshUser = useCallback(async () => {
    setIsLoading(true);
    try {
      const envelope = await getCurrentUser();
      setUser(envelope.user);
      if (!envelope.user && !isPublicPath) {
        const next = `${pathname}${searchParams.toString() ? `?${searchParams}` : ""}`;
        router.replace(`/login?next=${encodeURIComponent(next)}`);
      }
    } finally {
      setIsLoading(false);
    }
  }, [isPublicPath, pathname, router, searchParams]);

  const logout = useCallback(async () => {
    await logoutAccount();
    setUser(null);
    router.replace("/login");
  }, [router]);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const value = useMemo(
    () => ({ user, isLoading, refreshUser, logout }),
    [user, isLoading, refreshUser, logout],
  );

  if (isLoading && !isPublicPath) {
    return (
      <div className="grid min-h-screen place-items-center bg-paper text-sm font-semibold text-ink-light">
        正在确认登录状态...
      </div>
    );
  }

  if (!user && !isPublicPath) {
    return null;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
```

- [ ] **Step 6: Wrap the app in AuthProvider**

In `frontend/src/app/layout.tsx`, import and wrap children:

```tsx
import { AuthProvider } from "@/components/auth-provider";
```

Change the body content:

```tsx
<body className="font-sans antialiased min-h-screen bg-paper text-ink">
  <AuthProvider>{children}</AuthProvider>
</body>
```

- [ ] **Step 7: Run frontend auth tests green**

Run:

```bash
cd frontend
rtk npm test -- auth-flow
```

Expected: PASS.

- [ ] **Step 8: Commit**

Run:

```bash
rtk git add frontend/src/lib/auth-api.ts frontend/src/lib/agent-api.ts frontend/src/lib/image-api.ts frontend/src/components/auth-provider.tsx frontend/src/app/layout.tsx frontend/tests/auth-flow.test.mjs
rtk git commit -m "feat: add frontend auth session client"
```

---

### Task 6: Login, Register, Navigation, And Admin UI

**Files:**
- Create: `frontend/src/components/app-nav.tsx`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/register/page.tsx`
- Create: `frontend/src/app/admin/accounts/page.tsx`
- Modify: `frontend/src/app/page.tsx`
- Test: `frontend/tests/auth-flow.test.mjs`

- [ ] **Step 1: Add failing UI source tests**

Append to `frontend/tests/auth-flow.test.mjs`:

```javascript
test("login and register pages submit account forms", () => {
  const loginSource = readFileSync("src/app/login/page.tsx", "utf8");
  const registerSource = readFileSync("src/app/register/page.tsx", "utf8");

  assert.match(loginSource, /loginAccount/);
  assert.match(loginSource, /邮箱/);
  assert.match(loginSource, /密码/);
  assert.match(loginSource, /router\.replace/);
  assert.match(registerSource, /registerAccount/);
  assert.match(registerSource, /用户名/);
  assert.match(registerSource, /邮箱/);
  assert.match(registerSource, /密码/);
});

test("app navigation hides account management from regular users", () => {
  const source = readFileSync("src/components/app-nav.tsx", "utf8");

  assert.match(source, /user\?\.isAdmin/);
  assert.match(source, /\/admin\/accounts/);
  assert.match(source, /账号管理/);
  assert.match(source, /logout/);
});

test("admin accounts page does not provide admin promotion", () => {
  const source = readFileSync("src/app/admin/accounts/page.tsx", "utf8");

  assert.match(source, /listUsers/);
  assert.match(source, /updateUser/);
  assert.match(source, /resetUserPassword/);
  assert.match(source, /isActive/);
  assert.doesNotMatch(source, /isAdmin: true/);
  assert.doesNotMatch(source, /设置为管理员/);
});
```

- [ ] **Step 2: Run UI tests red**

Run:

```bash
cd frontend
rtk npm test -- auth-flow
```

Expected: FAIL because UI files do not exist.

- [ ] **Step 3: Create shared navigation**

Create `frontend/src/components/app-nav.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LogOut,
  MessageSquareText,
  Package,
  Settings2,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";

const baseItems = [
  { label: "商品图", href: "/", icon: Package },
  { label: "ChatGPT 对话", href: "/agent", icon: MessageSquareText },
];

export function AppNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const items = user?.isAdmin
    ? [...baseItems, { label: "账号管理", href: "/admin/accounts", icon: ShieldCheck }]
    : baseItems;

  return (
    <aside className="homepageRail hidden border-r border-border bg-surface px-5 py-7 xl:flex xl:flex-col">
      <Link href="/" className="block">
        <span className="block text-[21px] font-black leading-6 tracking-tight">
          图像指挥台
        </span>
        <span className="mt-2 block text-xs font-medium text-ink-light">
          电商商品图生成
        </span>
      </Link>

      <nav className="mt-8 grid gap-2" aria-label="主导航">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-refined ${
                active
                  ? "bg-ink text-white"
                  : "text-ink-light hover:bg-surface-soft hover:text-ink"
              }`}
            >
              <span
                className={`grid h-6 w-6 place-items-center rounded-md ${
                  active ? "bg-coral text-white" : "bg-paper-dim text-ink-light"
                }`}
              >
                <Icon aria-hidden="true" className="h-3.5 w-3.5" />
              </span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto grid gap-3 border-t border-border pt-4">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-ink">{user?.username}</p>
          <p className="truncate text-xs text-ink-light">{user?.email}</p>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="flex min-h-10 items-center gap-2 rounded-md border border-border px-3 text-sm font-semibold text-ink-light transition-refined hover:border-border-hover hover:text-ink"
        >
          <LogOut aria-hidden="true" className="h-4 w-4" />
          退出登录
        </button>
      </div>
    </aside>
  );
}
```

- [ ] **Step 4: Create login page**

Create `frontend/src/app/login/page.tsx`:

```tsx
"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { loginAccount } from "@/lib/auth-api";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await loginAccount({ email, password });
      await refreshUser();
      router.replace(searchParams.get("next") || "/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "登录失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-paper px-4 py-10 text-ink">
      <form
        onSubmit={handleSubmit}
        className="grid w-full max-w-sm gap-4 rounded-lg border border-border bg-surface p-6 shadow-soft"
      >
        <div>
          <h1 className="text-2xl font-black">登录</h1>
          <p className="mt-2 text-sm text-ink-light">继续使用商品图工作台。</p>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          邮箱
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            autoComplete="email"
            className="min-h-11 rounded-md border border-border bg-surface-soft px-3 outline-none focus:border-border-hover"
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          密码
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="current-password"
            className="min-h-11 rounded-md border border-border bg-surface-soft px-3 outline-none focus:border-border-hover"
          />
        </label>
        {error && <p className="text-sm font-semibold text-error">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="min-h-11 rounded-md bg-ink px-4 text-sm font-bold text-white transition-refined hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "正在登录..." : "登录"}
        </button>
        <p className="text-center text-sm text-ink-light">
          没有账号？{" "}
          <Link href="/register" className="font-semibold text-accent">
            注册
          </Link>
        </p>
      </form>
    </main>
  );
}
```

- [ ] **Step 5: Create register page**

Create `frontend/src/app/register/page.tsx` with the same layout as login, but using username and `registerAccount`:

```tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { registerAccount } from "@/lib/auth-api";

export default function RegisterPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await registerAccount({ email, username, password });
      await refreshUser();
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "注册失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-paper px-4 py-10 text-ink">
      <form
        onSubmit={handleSubmit}
        className="grid w-full max-w-sm gap-4 rounded-lg border border-border bg-surface p-6 shadow-soft"
      >
        <div>
          <h1 className="text-2xl font-black">注册</h1>
          <p className="mt-2 text-sm text-ink-light">第一个注册账号会成为管理员。</p>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          用户名
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            className="min-h-11 rounded-md border border-border bg-surface-soft px-3 outline-none focus:border-border-hover"
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          邮箱
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            type="email"
            autoComplete="email"
            className="min-h-11 rounded-md border border-border bg-surface-soft px-3 outline-none focus:border-border-hover"
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          密码
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            autoComplete="new-password"
            className="min-h-11 rounded-md border border-border bg-surface-soft px-3 outline-none focus:border-border-hover"
          />
        </label>
        {error && <p className="text-sm font-semibold text-error">{error}</p>}
        <button
          type="submit"
          disabled={isSubmitting}
          className="min-h-11 rounded-md bg-ink px-4 text-sm font-bold text-white transition-refined hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "正在注册..." : "注册"}
        </button>
        <p className="text-center text-sm text-ink-light">
          已有账号？{" "}
          <Link href="/login" className="font-semibold text-accent">
            登录
          </Link>
        </p>
      </form>
    </main>
  );
}
```

- [ ] **Step 6: Create admin account management page**

Create `frontend/src/app/admin/accounts/page.tsx`:

```tsx
"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppNav } from "@/components/app-nav";
import { useAuth } from "@/components/auth-provider";
import {
  listUsers,
  resetUserPassword,
  updateUser,
  type CurrentUser,
} from "@/lib/auth-api";

export default function AdminAccountsPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<CurrentUser[]>([]);
  const [error, setError] = useState("");
  const [passwords, setPasswords] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!user?.isAdmin) {
      return;
    }
    listUsers()
      .then((envelope) => setUsers(envelope.users))
      .catch((caught) =>
        setError(caught instanceof Error ? caught.message : "加载账号失败。"),
      );
  }, [user?.isAdmin]);

  if (!user?.isAdmin) {
    return (
      <main className="grid min-h-screen place-items-center bg-paper px-4 text-ink">
        <div className="rounded-lg border border-border bg-surface p-6 shadow-soft">
          <h1 className="text-xl font-black">无权访问</h1>
          <p className="mt-2 text-sm text-ink-light">账号管理仅管理员可用。</p>
        </div>
      </main>
    );
  }

  async function handleUserUpdate(target: CurrentUser, isActive: boolean) {
    setError("");
    try {
      const envelope = await updateUser(target.userId, { isActive });
      if (envelope.user) {
        setUsers((items) =>
          items.map((item) =>
            item.userId === envelope.user?.userId ? envelope.user : item,
          ),
        );
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "更新账号失败。");
    }
  }

  async function handleResetPassword(
    event: FormEvent<HTMLFormElement>,
    target: CurrentUser,
  ) {
    event.preventDefault();
    const password = passwords[target.userId] || "";
    setError("");
    try {
      await resetUserPassword(target.userId, password);
      setPasswords((items) => ({ ...items, [target.userId]: "" }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "重置密码失败。");
    }
  }

  return (
    <main className="homepageShell min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen xl:grid-cols-[10rem_minmax(0,1fr)]">
        <AppNav />
        <section className="min-w-0 px-4 py-5 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-6xl gap-5">
            <header>
              <h1 className="text-2xl font-black">账号管理</h1>
              <p className="mt-2 text-sm text-ink-light">
                管理用户信息、启停账号和重置密码。
              </p>
            </header>
            {error && (
              <p className="rounded-md border border-error/30 bg-white px-3 py-2 text-sm font-semibold text-error">
                {error}
              </p>
            )}
            <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-soft">
              <table className="w-full min-w-[760px] border-collapse text-left text-sm">
                <thead className="bg-surface-soft text-xs uppercase text-ink-light">
                  <tr>
                    <th className="px-4 py-3">用户</th>
                    <th className="px-4 py-3">邮箱</th>
                    <th className="px-4 py-3">身份</th>
                    <th className="px-4 py-3">状态</th>
                    <th className="px-4 py-3">重置密码</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((item) => (
                    <tr key={item.userId} className="border-t border-border">
                      <td className="px-4 py-3">
                        <div className="font-semibold">{item.username}</div>
                        <div className="text-xs text-ink-light">{item.userId}</div>
                      </td>
                      <td className="px-4 py-3">{item.email}</td>
                      <td className="px-4 py-3">
                        {item.isAdmin ? "管理员" : "普通用户"}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          disabled={item.userId === user.userId}
                          onClick={() => void handleUserUpdate(item, !item.isActive)}
                          className="rounded-md border border-border px-3 py-1.5 font-semibold text-ink-light transition-refined hover:border-border-hover hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {item.isActive ? "停用" : "启用"}
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <form
                          onSubmit={(event) => void handleResetPassword(event, item)}
                          className="flex gap-2"
                        >
                          <input
                            value={passwords[item.userId] || ""}
                            onChange={(event) =>
                              setPasswords((current) => ({
                                ...current,
                                [item.userId]: event.target.value,
                              }))
                            }
                            type="password"
                            placeholder="新密码"
                            className="min-h-9 w-36 rounded-md border border-border bg-surface-soft px-3 outline-none focus:border-border-hover"
                          />
                          <button
                            type="submit"
                            className="rounded-md bg-ink px-3 py-1.5 font-semibold text-white transition-refined hover:bg-accent"
                          >
                            保存
                          </button>
                        </form>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
```

- [ ] **Step 7: Replace homepage inline navigation**

In `frontend/src/app/page.tsx`, remove the local `navItems` array and lucide nav imports. Import:

```tsx
import { AppNav } from "@/components/app-nav";
```

Replace the `<aside ...>` block with:

```tsx
<AppNav />
```

- [ ] **Step 8: Run frontend UI tests green**

Run:

```bash
cd frontend
rtk npm test -- auth-flow
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
rtk git add frontend/src/components/app-nav.tsx frontend/src/app/login/page.tsx frontend/src/app/register/page.tsx frontend/src/app/admin/accounts/page.tsx frontend/src/app/page.tsx frontend/tests/auth-flow.test.mjs
rtk git commit -m "feat: add account management UI"
```

---

### Task 7: Full Verification And Polish

**Files:**
- Potentially modify any file touched above if verification finds issues.

- [ ] **Step 1: Run all backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend source tests**

Run:

```bash
cd frontend
rtk npm test
```

Expected: PASS.

- [ ] **Step 3: Run frontend lint**

Run:

```bash
cd frontend
rtk npm run lint
```

Expected: PASS.

- [ ] **Step 4: Run frontend production build**

Run:

```bash
cd frontend
rtk npm run build
```

Expected: PASS.

- [ ] **Step 5: Run database migration smoke check**

If local Docker services are running, run:

```bash
rtk backend/.venv/Scripts/python -m alembic -c backend/alembic.ini upgrade head
```

Expected: PASS and `users` table exists.

If no local database is running, record that migration smoke check was skipped because PostgreSQL was unavailable.

- [ ] **Step 6: Manual app smoke test**

Start the backend and frontend:

```bash
rtk backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --reload
cd frontend
rtk npm run dev
```

Open `http://localhost:3000` and verify:

- unauthenticated visit redirects to `/login`
- first registration signs in and shows the product workbench
- admin account link appears for first user
- second registration creates a normal user
- normal user cannot open `/admin/accounts`
- admin can list users, disable a normal user, and reset a password
- disabled user cannot log in

- [ ] **Step 7: Final commit**

If verification fixes were needed:

```bash
rtk git add <changed-files>
rtk git commit -m "fix: polish account management flow"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Registration with email, username, and password: Task 2 and Task 3.
- First registered account is administrator: Task 2 service tests and implementation.
- Administrator-only account management: Task 3 admin dependencies and routes, Task 6 admin UI.
- No complex permissions: only `is_admin` and `is_active`; no role or permission tables.
- No admin promotion: admin update schema and UI do not send or accept `isAdmin`.
- `users.user_id`: Task 1 model and migration, Task 2 generation and route usage.
- All app features require login: Task 4 protects existing image and agent APIs.

Placeholder scan:

- No `TBD`, `TODO`, or "implement later" entries remain.
- Each code creation step gives concrete file content or concrete code to add.

Type consistency:

- Backend exposes camelCase response fields through `UserDto`.
- Frontend uses `userId`, `isAdmin`, and `isActive` consistently.
- Admin routes use business `user_id` in paths and keep UUID `id` internal.
