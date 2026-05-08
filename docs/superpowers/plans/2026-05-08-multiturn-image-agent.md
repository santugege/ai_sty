# Multiturn Image Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a PostgreSQL-backed multi-turn image agent where `gpt-5.5` understands user instructions and calls a custom `gpt_image_2_edit` tool powered by `gpt-image-2`.

**Architecture:** Keep the existing one-shot `/api/images/generate` route. Add a separate `/api/agent` namespace backed by SQLAlchemy, PostgreSQL, local image storage, an agent decision service using `gpt-5.5`, and a whitelisted image tool that calls the OpenAI Images API with `gpt-image-2`.

**Tech Stack:** FastAPI, OpenAI Python SDK, SQLAlchemy 2.x, psycopg, Alembic, Pydantic, PostgreSQL, pytest, Next.js, React, TypeScript, node:test.

---

## File Structure

- Modify `backend/requirements.txt`: add PostgreSQL and migration dependencies.
- Modify `backend/.env.example`: add database, storage, and text agent model variables.
- Create `backend/alembic.ini`: Alembic config scoped to `backend/`.
- Create `backend/alembic/env.py`: migration environment using `app.db.Base`.
- Create `backend/alembic/script.py.mako`: migration template.
- Create `backend/alembic/versions/20260508_0001_agent_tables.py`: initial agent tables migration.
- Create `backend/app/db.py`: SQLAlchemy engine, session factory, and declarative base.
- Create `backend/app/agent_models.py`: SQLAlchemy rows for sessions, messages, and image versions.
- Create `backend/app/agent_schemas.py`: Pydantic request and response DTOs.
- Create `backend/app/image_storage.py`: local image byte storage and data URL decoding.
- Create `backend/app/agent_repository.py`: database persistence operations.
- Create `backend/app/agent_tools.py`: tool interface, registry, and `gpt_image_2_edit`.
- Create `backend/app/agent_openai.py`: `gpt-5.5` decision call through the Responses API.
- Create `backend/app/agent_service.py`: create session, send message, restore version.
- Modify `backend/app/main.py`: add `/api/agent` routes and dependency wiring.
- Create `backend/tests/test_agent_models.py`: SQLAlchemy model and metadata tests.
- Create `backend/tests/test_image_storage.py`: storage tests.
- Create `backend/tests/test_agent_repository.py`: repository tests.
- Create `backend/tests/test_agent_tools.py`: image tool registry and OpenAI wrapper tests.
- Create `backend/tests/test_agent_service.py`: service tests using fake planner and fake tool.
- Create `backend/tests/test_agent_routes.py`: FastAPI route tests.
- Create `frontend/src/lib/agent-api.ts`: typed client helpers for agent endpoints.
- Create `frontend/src/components/agent-image-workbench.tsx`: multi-turn chat and image version UI.
- Create `frontend/src/app/agent/page.tsx`: route for the agent workbench.
- Modify `frontend/src/app/page.tsx`: add a visible entry point to the agent workbench without removing existing product flow.
- Create `frontend/tests/agent-workbench.test.mjs`: source-level frontend tests.

## Model Contract

Implementation must keep these model responsibilities separate:

```env
OPENAI_AGENT_MODEL=gpt-5.5
OPENAI_IMAGE_MODEL=gpt-image-2
```

`OPENAI_AGENT_MODEL` is used only by the decision planner in `backend/app/agent_openai.py`.

`OPENAI_IMAGE_MODEL` is used only by `gpt_image_2_edit` in `backend/app/agent_tools.py`.

The agent can decide to call `gpt_image_2_edit`, but user prompts must never install tools, register tools, or execute arbitrary local code.

---

### Task 1: Backend Dependencies And Configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add failing dependency assertions**

Create `backend/tests/test_agent_dependencies.py`:

```python
from pathlib import Path


def test_backend_dependencies_include_postgres_agent_stack():
    requirements = Path("backend/requirements.txt").read_text(encoding="utf-8")

    assert "sqlalchemy" in requirements
    assert "psycopg[binary]" in requirements
    assert "alembic" in requirements


def test_env_example_includes_agent_configuration():
    env_example = Path("backend/.env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=" in env_example
    assert "IMAGE_STORAGE_DIR=" in env_example
    assert "OPENAI_AGENT_MODEL=gpt-5.5" in env_example
    assert "OPENAI_IMAGE_MODEL=gpt-image-2" in env_example
```

- [ ] **Step 2: Run dependency tests red**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_dependencies.py -q`

Expected: FAIL because the new dependencies and environment variables are not present.

- [ ] **Step 3: Update backend dependencies**

Append these lines to `backend/requirements.txt`:

```txt
sqlalchemy
psycopg[binary]
alembic
```

- [ ] **Step 4: Update environment example**

Append these lines to `backend/.env.example`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/image_agent
IMAGE_STORAGE_DIR=backend/storage/images
OPENAI_AGENT_MODEL=gpt-5.5
```

Keep the existing `OPENAI_IMAGE_MODEL=gpt-image-2` line.

- [ ] **Step 5: Install dependencies**

Run: `rtk backend/.venv/Scripts/python -m pip install -r backend/requirements.txt`

Expected: dependencies install successfully.

- [ ] **Step 6: Run dependency tests green**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_dependencies.py -q`

Expected: PASS.

---

### Task 2: SQLAlchemy Models And Alembic Migration

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/agent_models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/20260508_0001_agent_tables.py`
- Create: `backend/tests/test_agent_models.py`

- [ ] **Step 1: Write model metadata tests**

Create `backend/tests/test_agent_models.py`:

```python
from app.db import Base
from app.agent_models import AgentMessageRow, AgentSessionRow, ImageVersionRow


def test_agent_tables_are_registered():
    table_names = set(Base.metadata.tables)

    assert "agent_sessions" in table_names
    assert "agent_messages" in table_names
    assert "image_versions" in table_names


def test_agent_session_columns():
    columns = AgentSessionRow.__table__.columns

    assert "id" in columns
    assert "title" in columns
    assert "current_version_id" in columns
    assert "previous_response_id" in columns
    assert "status" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_image_version_parent_relationship_exists():
    columns = ImageVersionRow.__table__.columns

    assert "parent_version_id" in columns
    assert "storage_key" in columns
    assert "prompt" in columns
    assert "model" in columns


def test_agent_message_session_relationship_exists():
    assert AgentMessageRow.session.property.mapper.class_ is AgentSessionRow
```

- [ ] **Step 2: Run model tests red**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_models.py -q`

Expected: FAIL because `app.db` and `app.agent_models` do not exist.

- [ ] **Step 3: Create SQLAlchemy base and session helpers**

Create `backend/app/db.py`:

```python
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/image_agent",
    )


engine = create_engine(database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
```

- [ ] **Step 4: Create SQLAlchemy rows**

Create `backend/app/agent_models.py`:

```python
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

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, default="Untitled image session")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    previous_response_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    messages: Mapped[list[AgentMessageRow]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    versions: Mapped[list[ImageVersionRow]] = relationship(
        foreign_keys="ImageVersionRow.session_id",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class AgentMessageRow(Base):
    __tablename__ = "agent_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agent_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    response_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[AgentSessionRow] = relationship(back_populates="messages")


class ImageVersionRow(Base):
    __tablename__ = "image_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agent_sessions.id"), index=True)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("image_versions.id"),
        nullable=True,
    )
    storage_key: Mapped[str] = mapped_column(Text)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str] = mapped_column(Text, default="image/png")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    revised_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped[AgentSessionRow] = relationship(
        foreign_keys=[session_id],
        back_populates="versions",
    )
    parent_version: Mapped[ImageVersionRow | None] = relationship(
        remote_side=[id],
        foreign_keys=[parent_version_id],
    )
```

- [ ] **Step 5: Create Alembic files**

Create `backend/alembic.ini`:

```ini
[alembic]
script_location = backend/alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+psycopg://postgres:postgres@localhost:5432/image_agent

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

Create `backend/alembic/env.py`:

```python
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.agent_models import AgentMessageRow, AgentSessionRow, ImageVersionRow  # noqa: F401
from app.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url"),
    )


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create `backend/alembic/script.py.mako`:

```python
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Create `backend/alembic/versions/20260508_0001_agent_tables.py`:

```python
"""create agent tables

Revision ID: 20260508_0001
Revises:
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260508_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_response_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "agent_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_sessions.id"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("response_id", sa.Text(), nullable=True),
        sa.Column("tool_call_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_messages_session_id", "agent_messages", ["session_id"])
    op.create_table(
        "image_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_sessions.id"), nullable=False),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("image_versions.id"), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("revised_prompt", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_image_versions_session_id", "image_versions", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_image_versions_session_id", table_name="image_versions")
    op.drop_table("image_versions")
    op.drop_index("ix_agent_messages_session_id", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_table("agent_sessions")
```

- [ ] **Step 6: Run model tests green**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_models.py -q`

Expected: PASS.

---

### Task 3: Image Storage

**Files:**
- Create: `backend/app/image_storage.py`
- Create: `backend/tests/test_image_storage.py`

- [ ] **Step 1: Write image storage tests**

Create `backend/tests/test_image_storage.py`:

```python
import base64

from app.image_storage import LocalImageStorage, decode_data_url


def test_decode_data_url_returns_mime_type_and_bytes():
    encoded = base64.b64encode(b"image").decode("ascii")

    decoded = decode_data_url(f"data:image/png;base64,{encoded}")

    assert decoded.mime_type == "image/png"
    assert decoded.image_bytes == b"image"


def test_local_image_storage_writes_and_reads_bytes(tmp_path):
    storage = LocalImageStorage(tmp_path)

    stored = storage.write_image(b"image", mime_type="image/png")

    assert stored.storage_key.endswith(".png")
    assert stored.mime_type == "image/png"
    assert storage.read_image(stored.storage_key) == b"image"
```

- [ ] **Step 2: Run image storage tests red**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_storage.py -q`

Expected: FAIL because `app.image_storage` does not exist.

- [ ] **Step 3: Implement local image storage**

Create `backend/app/image_storage.py`:

```python
from __future__ import annotations

import base64
import os
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DecodedImage:
    mime_type: str
    image_bytes: bytes


@dataclass(frozen=True)
class StoredImage:
    storage_key: str
    mime_type: str
    public_url: str | None = None


def decode_data_url(src: str) -> DecodedImage:
    if not src.startswith("data:") or ";base64," not in src:
        raise ValueError("Expected a base64 data URL image.")

    header, encoded = src.split(";base64,", 1)
    mime_type = header.removeprefix("data:")
    return DecodedImage(mime_type=mime_type, image_bytes=base64.b64decode(encoded))


def extension_for_mime_type(mime_type: str) -> str:
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".png"


class LocalImageStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or os.getenv("IMAGE_STORAGE_DIR", "backend/storage/images"))
        self.root.mkdir(parents=True, exist_ok=True)

    def write_image(self, image_bytes: bytes, mime_type: str = "image/png") -> StoredImage:
        storage_key = f"{uuid.uuid4()}{extension_for_mime_type(mime_type)}"
        path = self.root / storage_key
        path.write_bytes(image_bytes)
        return StoredImage(storage_key=storage_key, mime_type=mime_type)

    def read_image(self, storage_key: str) -> bytes:
        return (self.root / storage_key).read_bytes()
```

- [ ] **Step 4: Run image storage tests green**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_storage.py -q`

Expected: PASS.

---

### Task 4: Repository Layer

**Files:**
- Create: `backend/app/agent_repository.py`
- Create: `backend/tests/test_agent_repository.py`

- [ ] **Step 1: Write repository tests**

Create `backend/tests/test_agent_repository.py`:

```python
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent_repository import AgentRepository
from app.db import Base


def make_repo():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    return AgentRepository(session)


def test_create_session_persists_initial_version_and_message():
    repo = make_repo()

    session = repo.create_session(title="Product edit")
    version = repo.add_image_version(
        session_id=session.id,
        parent_version_id=None,
        storage_key="initial.png",
        mime_type="image/png",
        prompt="Initial upload",
        model="user-upload",
    )
    repo.add_message(session.id, role="user", content="Make it brighter")
    repo.set_current_version(session.id, version.id)

    loaded = repo.get_session_state(session.id)

    assert loaded.session.id == session.id
    assert loaded.session.current_version_id == version.id
    assert len(loaded.messages) == 1
    assert len(loaded.versions) == 1


def test_restore_version_updates_only_current_version():
    repo = make_repo()
    session = repo.create_session(title="Product edit")
    first = repo.add_image_version(session.id, None, "one.png", "image/png", "one", "gpt-image-2")
    second = repo.add_image_version(session.id, first.id, "two.png", "image/png", "two", "gpt-image-2")
    repo.set_current_version(session.id, second.id)

    repo.restore_version(session.id, first.id)
    loaded = repo.get_session_state(session.id)

    assert loaded.session.current_version_id == first.id
    assert [version.id for version in loaded.versions] == [first.id, second.id]


def test_missing_session_returns_none():
    repo = make_repo()

    assert repo.get_session_state(uuid.uuid4()) is None
```

- [ ] **Step 2: Run repository tests red**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_repository.py -q`

Expected: FAIL because `app.agent_repository` does not exist.

- [ ] **Step 3: Implement repository**

Create `backend/app/agent_repository.py`:

```python
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

    def set_current_version(self, session_id: uuid.UUID, version_id: uuid.UUID) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return
        session.current_version_id = version_id
        self.db.commit()

    def set_previous_response_id(self, session_id: uuid.UUID, response_id: str | None) -> None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return
        session.previous_response_id = response_id
        self.db.commit()

    def restore_version(self, session_id: uuid.UUID, version_id: uuid.UUID) -> None:
        version = self.db.get(ImageVersionRow, version_id)
        if version is None or version.session_id != session_id:
            return
        self.set_current_version(session_id, version_id)

    def get_session_state(self, session_id: uuid.UUID) -> AgentSessionState | None:
        session = self.db.get(AgentSessionRow, session_id)
        if session is None:
            return None
        messages = list(
            self.db.scalars(
                select(AgentMessageRow)
                .where(AgentMessageRow.session_id == session_id)
                .order_by(AgentMessageRow.created_at)
            )
        )
        versions = list(
            self.db.scalars(
                select(ImageVersionRow)
                .where(ImageVersionRow.session_id == session_id)
                .order_by(ImageVersionRow.created_at)
            )
        )
        return AgentSessionState(session=session, messages=messages, versions=versions)
```

- [ ] **Step 4: Run repository tests green**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_repository.py -q`

Expected: PASS.

---

### Task 5: Agent Schemas And Tool Registry

**Files:**
- Create: `backend/app/agent_schemas.py`
- Create: `backend/app/agent_tools.py`
- Create: `backend/tests/test_agent_tools.py`

- [ ] **Step 1: Write tool registry tests**

Create `backend/tests/test_agent_tools.py`:

```python
from app.agent_tools import AgentToolContext, AgentToolRegistry, GptImage2EditTool


def test_registry_contains_gpt_image_2_edit_tool():
    registry = AgentToolRegistry([GptImage2EditTool(image_client=lambda context: None)])

    tool = registry.get("gpt_image_2_edit")

    assert tool is not None
    assert tool.name == "gpt_image_2_edit"


def test_gpt_image_2_edit_tool_uses_image_model():
    calls = []

    def fake_image_client(context):
        calls.append(context)
        return b"edited"

    tool = GptImage2EditTool(image_client=fake_image_client, image_model="gpt-image-2")
    result = tool.execute(
        AgentToolContext(
            image_bytes=b"input",
            image_name="product.png",
            mime_type="image/png",
            instruction="Make the background white",
            size="1536x1024",
        )
    )

    assert result.image_bytes == b"edited"
    assert result.model == "gpt-image-2"
    assert calls[0].instruction == "Make the background white"
```

- [ ] **Step 2: Run tool tests red**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_tools.py -q`

Expected: FAIL because `app.agent_tools` does not exist.

- [ ] **Step 3: Create response schemas**

Create `backend/app/agent_schemas.py`:

```python
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
```

- [ ] **Step 4: Implement tool registry**

Create `backend/app/agent_tools.py`:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Protocol


@dataclass(frozen=True)
class AgentToolContext:
    image_bytes: bytes
    image_name: str
    mime_type: str
    instruction: str
    size: str


@dataclass(frozen=True)
class AgentToolResult:
    image_bytes: bytes
    mime_type: str
    prompt: str
    revised_prompt: str | None
    model: str


class AgentTool(Protocol):
    name: str
    description: str

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        ...


class AgentToolRegistry:
    def __init__(self, tools: list[AgentTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)


class GptImage2EditTool:
    name = "gpt_image_2_edit"
    description = "Edit the current product image using gpt-image-2."

    def __init__(
        self,
        image_client: Callable[[AgentToolContext], bytes],
        image_model: str | None = None,
    ) -> None:
        self.image_client = image_client
        self.image_model = image_model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        image_bytes = self.image_client(context)
        return AgentToolResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt=None,
            model=self.image_model,
        )
```

- [ ] **Step 5: Run tool registry tests green**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_tools.py -q`

Expected: PASS.

---

### Task 6: OpenAI Image Tool And Agent Decision Planner

**Files:**
- Modify: `backend/app/agent_tools.py`
- Create: `backend/app/agent_openai.py`
- Modify: `backend/tests/test_agent_tools.py`
- Create: `backend/tests/test_agent_openai.py`

- [ ] **Step 1: Add tests for OpenAI image client**

Append to `backend/tests/test_agent_tools.py`:

```python
from app.agent_tools import create_openai_image_client


def test_openai_image_client_calls_images_edit_with_gpt_image_2():
    class FakeImages:
        def __init__(self):
            self.kwargs = None

        def edit(self, **kwargs):
            self.kwargs = kwargs
            return {"data": [{"b64_json": "ZWRpdGVk"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    output = image_client(
        AgentToolContext(
            image_bytes=b"input",
            image_name="product.png",
            mime_type="image/png",
            instruction="Make it brighter",
            size="1536x1024",
        )
    )

    assert output == b"edited"
    assert fake_client.images.kwargs["model"] == "gpt-image-2"
    assert fake_client.images.kwargs["prompt"] == "Make it brighter"
```

- [ ] **Step 2: Add tests for `gpt-5.5` planner**

Create `backend/tests/test_agent_openai.py`:

```python
from types import SimpleNamespace

from app.agent_openai import request_agent_decision


def test_agent_decision_uses_gpt_5_5_model():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_123",
                output_text='{"action":"edit","assistant_message":"I will edit it.","tool_name":"gpt_image_2_edit","tool_instruction":"Make it brighter."}',
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_agent_decision(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="Make it brighter",
        current_image_summary="Current product image exists.",
        recent_messages=[],
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert calls[0]["model"] == "gpt-5.5"
    assert decision.action == "edit"
    assert decision.tool_name == "gpt_image_2_edit"
    assert decision.response_id == "resp_123"
```

- [ ] **Step 3: Run OpenAI tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_tools.py backend/tests/test_agent_openai.py -q
```

Expected: FAIL because `create_openai_image_client` and `agent_openai.py` do not exist.

- [ ] **Step 4: Implement OpenAI image client**

Append to `backend/app/agent_tools.py`:

```python
import base64
from io import BytesIO
from typing import Any

from openai import OpenAI


def _read(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def create_openai_image_client(
    api_key: str,
    image_model: str,
    client_factory: Callable[..., Any] = OpenAI,
) -> Callable[[AgentToolContext], bytes]:
    def edit_image(context: AgentToolContext) -> bytes:
        client = client_factory(api_key=api_key)
        image_file = BytesIO(context.image_bytes)
        image_file.name = context.image_name
        response = client.images.edit(
            model=image_model,
            image=image_file,
            prompt=context.instruction,
            size=context.size,
            quality="auto",
        )
        data = _read(response, "data") or []
        first = data[0] if data else None
        if first is None:
            raise RuntimeError("OpenAI did not return an image result.")
        b64_json = _read(first, "b64_json")
        if not b64_json:
            raise RuntimeError("OpenAI did not return base64 image data.")
        return base64.b64decode(b64_json)

    return edit_image
```

- [ ] **Step 5: Implement agent decision planner**

Create `backend/app/agent_openai.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI


@dataclass(frozen=True)
class AgentTurnDecision:
    action: Literal["edit", "clarify"]
    assistant_message: str
    tool_name: str | None
    tool_instruction: str | None
    response_id: str | None


def request_agent_decision(
    api_key: str,
    agent_model: str,
    user_message: str,
    current_image_summary: str,
    recent_messages: list[dict[str, str]],
    previous_response_id: str | None,
    client_factory: type[Any] = OpenAI,
) -> AgentTurnDecision:
    client = client_factory(api_key=api_key)
    response = client.responses.create(
        model=agent_model,
        previous_response_id=previous_response_id,
        input=[
            {
                "role": "system",
                "content": (
                    "You are an ecommerce image editing agent. "
                    "Decide whether the user's request is clear enough to edit the current image. "
                    "Return JSON only with action, assistant_message, tool_name, and tool_instruction. "
                    "Use tool_name gpt_image_2_edit only when action is edit."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "current_image_summary": current_image_summary,
                        "recent_messages": recent_messages,
                        "latest_user_message": user_message,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    )
    payload = json.loads(response.output_text)
    action = payload["action"]
    return AgentTurnDecision(
        action=action,
        assistant_message=payload["assistant_message"],
        tool_name=payload.get("tool_name"),
        tool_instruction=payload.get("tool_instruction"),
        response_id=getattr(response, "id", None),
    )
```

- [ ] **Step 6: Run OpenAI tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_tools.py backend/tests/test_agent_openai.py -q
```

Expected: PASS.

---

### Task 7: Agent Service

**Files:**
- Create: `backend/app/agent_service.py`
- Create: `backend/tests/test_agent_service.py`

- [ ] **Step 1: Write service tests**

Create `backend/tests/test_agent_service.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agent_openai import AgentTurnDecision
from app.agent_repository import AgentRepository
from app.agent_service import ImageAgentService
from app.agent_tools import AgentToolContext, AgentToolResult
from app.db import Base
from app.image_storage import LocalImageStorage


def make_service(tmp_path, decision):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    repo = AgentRepository(db)
    storage = LocalImageStorage(tmp_path)

    def fake_planner(**kwargs):
        return decision

    class FakeTool:
        name = "gpt_image_2_edit"
        description = "fake"

        def execute(self, context: AgentToolContext) -> AgentToolResult:
            return AgentToolResult(
                image_bytes=b"edited",
                mime_type="image/png",
                prompt=context.instruction,
                revised_prompt="edited prompt",
                model="gpt-image-2",
            )

    return ImageAgentService(repo, storage, fake_planner, {"gpt_image_2_edit": FakeTool()})


def test_create_session_with_clear_request_creates_child_version(tmp_path):
    service = make_service(
        tmp_path,
        AgentTurnDecision(
            action="edit",
            assistant_message="I edited the image.",
            tool_name="gpt_image_2_edit",
            tool_instruction="Make it brighter.",
            response_id="resp_123",
        ),
    )

    envelope = service.create_session(
        instruction="Make it brighter",
        image_bytes=b"initial",
        image_name="product.png",
        mime_type="image/png",
        size="1536x1024",
    )

    assert envelope.session.previousResponseId == "resp_123"
    assert len(envelope.versions) == 2
    assert envelope.currentImage.model == "gpt-image-2"
    assert envelope.pendingQuestion is None


def test_follow_up_can_return_clarifying_question_without_new_version(tmp_path):
    service = make_service(
        tmp_path,
        AgentTurnDecision(
            action="clarify",
            assistant_message="Which background style do you want?",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_456",
        ),
    )
    created = service.create_session(
        instruction="Initial upload",
        image_bytes=b"initial",
        image_name="product.png",
        mime_type="image/png",
        size="1536x1024",
    )

    envelope = service.send_message(created.session.id, "Make it better", size="1536x1024")

    assert envelope.pendingQuestion == "Which background style do you want?"
```

- [ ] **Step 2: Run service tests red**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_service.py -q`

Expected: FAIL because `app.agent_service` does not exist.

- [ ] **Step 3: Implement service**

Create `backend/app/agent_service.py` with these responsibilities:

```python
from __future__ import annotations

import base64
import uuid
from collections.abc import Callable

from app.agent_openai import AgentTurnDecision
from app.agent_repository import AgentRepository, AgentSessionState
from app.agent_schemas import AgentEnvelope, AgentMessageDto, AgentSessionDto, ImageVersionDto
from app.agent_tools import AgentToolContext, AgentToolResult
from app.image_storage import LocalImageStorage


Planner = Callable[..., AgentTurnDecision]


class AgentServiceError(Exception):
    status_code = 500


class AgentInputError(AgentServiceError):
    status_code = 400


class ImageAgentService:
    def __init__(
        self,
        repo: AgentRepository,
        storage: LocalImageStorage,
        planner: Planner,
        tools: dict[str, object],
    ) -> None:
        self.repo = repo
        self.storage = storage
        self.planner = planner
        self.tools = tools

    def create_session(
        self,
        instruction: str,
        image_bytes: bytes,
        image_name: str,
        mime_type: str,
        size: str,
    ) -> AgentEnvelope:
        if not instruction.strip():
            raise AgentInputError("Please enter an edit instruction.")
        if not image_bytes:
            raise AgentInputError("Please upload the initial product image.")

        session = self.repo.create_session(title=instruction[:80] or "Image session")
        stored = self.storage.write_image(image_bytes, mime_type=mime_type)
        initial = self.repo.add_image_version(
            session.id,
            None,
            stored.storage_key,
            stored.mime_type,
            "Initial upload",
            "user-upload",
        )
        self.repo.set_current_version(session.id, initial.id)
        self.repo.add_message(session.id, "user", instruction)
        return self._run_turn(session.id, instruction, size)

    def send_message(self, session_id: uuid.UUID, instruction: str, size: str) -> AgentEnvelope:
        if not instruction.strip():
            raise AgentInputError("Please enter an edit instruction.")
        self.repo.add_message(session_id, "user", instruction)
        return self._run_turn(session_id, instruction, size)

    def restore_version(self, session_id: uuid.UUID, version_id: uuid.UUID) -> AgentEnvelope:
        self.repo.restore_version(session_id, version_id)
        state = self.repo.get_session_state(session_id)
        if state is None:
            raise AgentInputError("Session not found.")
        return self._envelope(state)

    def get_session(self, session_id: uuid.UUID) -> AgentEnvelope:
        state = self.repo.get_session_state(session_id)
        if state is None:
            raise AgentInputError("Session not found.")
        return self._envelope(state)

    def _run_turn(self, session_id: uuid.UUID, instruction: str, size: str) -> AgentEnvelope:
        state = self.repo.get_session_state(session_id)
        if state is None:
            raise AgentInputError("Session not found.")
        current = self._current_version(state)
        if current is None:
            raise AgentInputError("Session has no active image.")

        decision = self.planner(
            user_message=instruction,
            current_image_summary=f"Active image version {current.id}",
            recent_messages=[{"role": message.role, "content": message.content} for message in state.messages[-8:]],
            previous_response_id=state.session.previous_response_id,
        )
        self.repo.set_previous_response_id(session_id, decision.response_id)
        self.repo.add_message(session_id, "assistant", decision.assistant_message, response_id=decision.response_id)

        if decision.action == "clarify":
            return self._envelope(self.repo.get_session_state(session_id), pending_question=decision.assistant_message)

        tool = self.tools.get(decision.tool_name or "")
        if tool is None:
            raise AgentServiceError("The selected agent tool is not available.")

        result: AgentToolResult = tool.execute(
            AgentToolContext(
                image_bytes=self.storage.read_image(current.storage_key),
                image_name="current.png",
                mime_type=current.mime_type,
                instruction=decision.tool_instruction or instruction,
                size=size,
            )
        )
        stored = self.storage.write_image(result.image_bytes, result.mime_type)
        version = self.repo.add_image_version(
            session_id,
            current.id,
            stored.storage_key,
            stored.mime_type,
            result.prompt,
            result.model,
            revised_prompt=result.revised_prompt,
        )
        self.repo.set_current_version(session_id, version.id)
        return self._envelope(self.repo.get_session_state(session_id))

    def _current_version(self, state: AgentSessionState):
        return next(
            (version for version in state.versions if version.id == state.session.current_version_id),
            None,
        )

    def _src_for_storage_key(self, storage_key: str, mime_type: str) -> str:
        encoded = base64.b64encode(self.storage.read_image(storage_key)).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _envelope(self, state: AgentSessionState | None, pending_question: str | None = None) -> AgentEnvelope:
        if state is None:
            raise AgentInputError("Session not found.")
        versions = [
            ImageVersionDto(
                id=version.id,
                sessionId=version.session_id,
                parentVersionId=version.parent_version_id,
                src=self._src_for_storage_key(version.storage_key, version.mime_type),
                storageKey=version.storage_key,
                mimeType=version.mime_type,
                width=version.width,
                height=version.height,
                prompt=version.prompt,
                revisedPrompt=version.revised_prompt,
                model=version.model,
                createdAt=version.created_at,
            )
            for version in state.versions
        ]
        current = next(
            (version for version in versions if version.id == state.session.current_version_id),
            None,
        )
        return AgentEnvelope(
            session=AgentSessionDto(
                id=state.session.id,
                title=state.session.title,
                currentVersionId=state.session.current_version_id,
                previousResponseId=state.session.previous_response_id,
                status=state.session.status,
                createdAt=state.session.created_at,
                updatedAt=state.session.updated_at,
            ),
            messages=[
                AgentMessageDto(
                    id=message.id,
                    sessionId=message.session_id,
                    role=message.role,
                    content=message.content,
                    responseId=message.response_id,
                    toolCallId=message.tool_call_id,
                    createdAt=message.created_at,
                )
                for message in state.messages
            ],
            currentImage=current,
            versions=versions,
            pendingQuestion=pending_question,
            error=None,
        )
```

- [ ] **Step 4: Run service tests green**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_service.py -q`

Expected: PASS.

---

### Task 8: FastAPI Agent Routes

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_agent_routes.py`

- [ ] **Step 1: Write route tests**

Create `backend/tests/test_agent_routes.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_agent_session_requires_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/agent/sessions",
        data={"instruction": "Make it brighter", "size": "1536x1024"},
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_agent_session_routes_exist():
    routes = {route.path for route in app.routes}

    assert "/api/agent/sessions" in routes
    assert "/api/agent/sessions/{session_id}/messages" in routes
    assert "/api/agent/sessions/{session_id}" in routes
    assert "/api/agent/sessions/{session_id}/versions/{version_id}/restore" in routes
```

- [ ] **Step 2: Run route tests red**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_routes.py -q`

Expected: FAIL because the routes do not exist.

- [ ] **Step 3: Add route wiring**

Modify `backend/app/main.py`:

```python
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agent_openai import request_agent_decision
from app.agent_repository import AgentRepository
from app.agent_service import AgentInputError, AgentServiceError, ImageAgentService
from app.agent_tools import GptImage2EditTool, create_openai_image_client
from app.db import get_db_session
from app.image_storage import LocalImageStorage
```

Add this helper:

```python
def build_agent_service(db: Session) -> ImageAgentService:
    api_key = os.getenv("OPENAI_API_KEY") or ""
    image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    agent_model = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.5")
    image_client = create_openai_image_client(api_key=api_key, image_model=image_model)

    def planner(**kwargs):
        return request_agent_decision(
            api_key=api_key,
            agent_model=agent_model,
            **kwargs,
        )

    return ImageAgentService(
        AgentRepository(db),
        LocalImageStorage(),
        planner,
        {"gpt_image_2_edit": GptImage2EditTool(image_client=image_client, image_model=image_model)},
    )
```

Add these routes:

```python
@app.post("/api/agent/sessions")
async def create_agent_session(
    instruction: str = Form(""),
    size: str = Form("1536x1024"),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db_session),
):
    try:
        if image is None:
            raise AgentInputError("Please upload the initial product image.")
        service = build_agent_service(db)
        return service.create_session(
            instruction=instruction,
            image_bytes=await image.read(),
            image_name=image.filename or "product.png",
            mime_type=image.content_type or "image/png",
            size=size,
        ).model_dump(mode="json")
    except AgentInputError as error:
        return JSONResponse({"error": str(error)}, status_code=error.status_code)
    except AgentServiceError as error:
        logger.exception("Agent service failed")
        return JSONResponse({"error": str(error)}, status_code=error.status_code)


@app.post("/api/agent/sessions/{session_id}/messages")
async def send_agent_message(
    session_id: UUID,
    payload: dict[str, str],
    db: Session = Depends(get_db_session),
):
    try:
        service = build_agent_service(db)
        return service.send_message(
            session_id,
            payload.get("instruction", ""),
            payload.get("size", "1536x1024"),
        ).model_dump(mode="json")
    except AgentInputError as error:
        return JSONResponse({"error": str(error)}, status_code=error.status_code)
    except AgentServiceError as error:
        logger.exception("Agent service failed")
        return JSONResponse({"error": str(error)}, status_code=error.status_code)


@app.get("/api/agent/sessions/{session_id}")
def get_agent_session(session_id: UUID, db: Session = Depends(get_db_session)):
    try:
        return build_agent_service(db).get_session(session_id).model_dump(mode="json")
    except AgentInputError as error:
        return JSONResponse({"error": str(error)}, status_code=error.status_code)


@app.post("/api/agent/sessions/{session_id}/versions/{version_id}/restore")
def restore_agent_version(
    session_id: UUID,
    version_id: UUID,
    db: Session = Depends(get_db_session),
):
    try:
        return build_agent_service(db).restore_version(session_id, version_id).model_dump(mode="json")
    except AgentInputError as error:
        return JSONResponse({"error": str(error)}, status_code=error.status_code)
```

- [ ] **Step 4: Run route tests green**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_routes.py -q`

Expected: PASS.

---

### Task 9: Frontend Agent API Client

**Files:**
- Create: `frontend/src/lib/agent-api.ts`
- Create: `frontend/tests/agent-workbench.test.mjs`

- [ ] **Step 1: Write frontend API source tests**

Create `frontend/tests/agent-workbench.test.mjs`:

```js
import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

test("agent api client calls the agent routes", () => {
  const source = readFileSync("src/lib/agent-api.ts", "utf8");

  assert.match(source, /\/api\/agent\/sessions/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /sendAgentMessage/);
  assert.match(source, /restoreAgentVersion/);
});
```

- [ ] **Step 2: Run frontend agent API tests red**

Run: `rtk npm test --prefix frontend -- agent-workbench.test.mjs`

Expected: FAIL because `src/lib/agent-api.ts` does not exist.

- [ ] **Step 3: Implement frontend agent API client**

Create `frontend/src/lib/agent-api.ts`:

```ts
const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type AgentMessage = {
  id: string;
  sessionId: string;
  role: "user" | "assistant" | "tool";
  content: string;
  responseId?: string | null;
  toolCallId?: string | null;
  createdAt: string;
};

export type AgentImageVersion = {
  id: string;
  sessionId: string;
  parentVersionId?: string | null;
  src: string;
  storageKey: string;
  mimeType: string;
  width?: number | null;
  height?: number | null;
  prompt: string;
  revisedPrompt?: string | null;
  model: string;
  createdAt: string;
};

export type AgentEnvelope = {
  session: {
    id: string;
    title: string;
    currentVersionId?: string | null;
    previousResponseId?: string | null;
    status: string;
    createdAt: string;
    updatedAt: string;
  };
  messages: AgentMessage[];
  currentImage?: AgentImageVersion | null;
  versions: AgentImageVersion[];
  pendingQuestion?: string | null;
  error?: string | null;
};

export async function createAgentSession(formData: FormData) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions`, {
      method: "POST",
      body: formData,
    }),
  );
}

export async function sendAgentMessage(sessionId: string, instruction: string, size: string) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ instruction, size }),
    }),
  );
}

export async function restoreAgentVersion(sessionId: string, versionId: string) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions/${sessionId}/versions/${versionId}/restore`, {
      method: "POST",
    }),
  );
}

async function readAgentResponse(response: Response): Promise<AgentEnvelope> {
  const payload = (await response.json()) as AgentEnvelope | { error?: string };

  if (!response.ok || "error" in payload) {
    throw new Error(payload.error || "Agent request failed.");
  }

  return payload as AgentEnvelope;
}
```

- [ ] **Step 4: Run frontend agent API tests green**

Run: `rtk npm test --prefix frontend -- agent-workbench.test.mjs`

Expected: PASS.

---

### Task 10: Frontend Conversation Workbench

**Files:**
- Create: `frontend/src/components/agent-image-workbench.tsx`
- Create: `frontend/src/app/agent/page.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/tests/agent-workbench.test.mjs`

- [ ] **Step 1: Extend frontend tests**

Append to `frontend/tests/agent-workbench.test.mjs`:

```js
test("agent workbench renders chat, current image, and version restore controls", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /createAgentSession/);
  assert.match(source, /sendAgentMessage/);
  assert.match(source, /restoreAgentVersion/);
  assert.match(source, /versions\.map/);
  assert.match(source, /textarea/);
});

test("agent route renders the workbench", () => {
  const source = readFileSync("src/app/agent/page.tsx", "utf8");

  assert.match(source, /AgentImageWorkbench/);
});
```

- [ ] **Step 2: Run frontend workbench tests red**

Run: `rtk npm test --prefix frontend -- agent-workbench.test.mjs`

Expected: FAIL because the component and page do not exist.

- [ ] **Step 3: Create agent workbench component**

Create `frontend/src/components/agent-image-workbench.tsx` as a client component. It must:

- Keep `file`, `instruction`, `session`, `messages`, `currentImage`, `versions`, `size`, `error`, and `isSubmitting` in React state.
- On first submit, build `FormData` with `instruction`, `size`, and `image`, then call `createAgentSession`.
- On follow-up submit, call `sendAgentMessage(session.id, instruction, size)`.
- Render `currentImage.src` in the main canvas.
- Render `messages` as a chat thread.
- Render `versions.map(...)` as a version strip with a restore button for each version.
- Call `restoreAgentVersion(session.id, version.id)` when restoring.

Use this component skeleton:

```tsx
"use client";

/* eslint-disable @next/next/no-img-element */

import { useState, type FormEvent } from "react";
import {
  createAgentSession,
  restoreAgentVersion,
  sendAgentMessage,
  type AgentEnvelope,
  type AgentImageVersion,
  type AgentMessage,
} from "@/lib/agent-api";

export function AgentImageWorkbench() {
  const [file, setFile] = useState<File | null>(null);
  const [instruction, setInstruction] = useState("");
  const [size, setSize] = useState("1536x1024");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [currentImage, setCurrentImage] = useState<AgentImageVersion | null>(null);
  const [versions, setVersions] = useState<AgentImageVersion[]>([]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function applyEnvelope(envelope: AgentEnvelope) {
    setSessionId(envelope.session.id);
    setMessages(envelope.messages);
    setCurrentImage(envelope.currentImage ?? null);
    setVersions(envelope.versions);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!instruction.trim() || isSubmitting) {
      return;
    }

    setError("");
    setIsSubmitting(true);

    try {
      const envelope = sessionId
        ? await sendAgentMessage(sessionId, instruction, size)
        : await createFirstSession();
      applyEnvelope(envelope);
      setInstruction("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Agent request failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function createFirstSession() {
    const formData = new FormData();
    formData.append("instruction", instruction);
    formData.append("size", size);
    if (file) {
      formData.append("image", file);
    }
    return createAgentSession(formData);
  }

  async function handleRestore(versionId: string) {
    if (!sessionId) {
      return;
    }
    applyEnvelope(await restoreAgentVersion(sessionId, versionId));
  }

  return (
    <main className="min-h-screen bg-paper px-4 py-6 text-ink sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-[1800px] gap-4 xl:grid-cols-[22rem_minmax(0,1fr)_24rem]">
        <aside className="rounded-2xl border border-border bg-surface p-5">
          <h1 className="font-serif text-3xl font-light">Multi-turn Image Agent</h1>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-6 block w-full text-sm"
          />
          <select
            value={size}
            onChange={(event) => setSize(event.target.value)}
            className="mt-4 w-full rounded-xl border border-border bg-paper-subtle px-3 py-2 text-sm"
          >
            <option value="1024x1024">1024x1024</option>
            <option value="1536x1024">1536x1024</option>
            <option value="1024x1536">1024x1536</option>
          </select>
        </aside>

        <section className="min-h-[42rem] rounded-2xl border border-border bg-[#090c12] p-4">
          {currentImage ? (
            <img src={currentImage.src} alt="Current generated result" className="h-full w-full rounded-xl object-contain" />
          ) : (
            <div className="grid h-full place-items-center text-sm text-ink-lighter">
              Upload an image and describe the first edit.
            </div>
          )}
        </section>

        <aside className="flex min-h-[42rem] flex-col rounded-2xl border border-border bg-surface p-5">
          <div className="flex-1 space-y-3 overflow-y-auto">
            {messages.map((message) => (
              <div key={message.id} className="rounded-xl border border-border bg-paper-subtle p-3 text-sm">
                <p className="font-mono text-[10px] uppercase text-ink-lighter">{message.role}</p>
                <p className="mt-2 leading-6">{message.content}</p>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-2 overflow-x-auto">
            {versions.map((version) => (
              <button
                key={version.id}
                type="button"
                onClick={() => handleRestore(version.id)}
                className="h-16 w-16 shrink-0 overflow-hidden rounded-lg border border-border"
              >
                <img src={version.src} alt="Version thumbnail" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
          <form onSubmit={handleSubmit} className="mt-4">
            <textarea
              value={instruction}
              onChange={(event) => setInstruction(event.target.value)}
              placeholder="Describe the next edit"
              rows={4}
              className="w-full resize-none rounded-xl border border-border bg-paper-subtle p-3 text-sm"
            />
            {error && <p className="mt-2 text-sm text-error">{error}</p>}
            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-3 w-full rounded-xl bg-coral px-4 py-3 text-sm font-semibold text-paper disabled:opacity-60"
            >
              {isSubmitting ? "Working..." : sessionId ? "Send edit" : "Start session"}
            </button>
          </form>
        </aside>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: Create route page**

Create `frontend/src/app/agent/page.tsx`:

```tsx
import { AgentImageWorkbench } from "@/components/agent-image-workbench";

export default function AgentPage() {
  return <AgentImageWorkbench />;
}
```

- [ ] **Step 5: Add homepage entry**

Modify `frontend/src/app/page.tsx` to include a link to `/agent` near the primary product workbench entry. The source should include:

```tsx
<a href="/agent">多轮图片 Agent</a>
```

- [ ] **Step 6: Run frontend workbench tests green**

Run: `rtk npm test --prefix frontend -- agent-workbench.test.mjs`

Expected: PASS.

---

### Task 11: Verification

**Files:**
- All modified backend and frontend files.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_dependencies.py backend/tests/test_agent_models.py backend/tests/test_image_storage.py backend/tests/test_agent_repository.py backend/tests/test_agent_tools.py backend/tests/test_agent_openai.py backend/tests/test_agent_service.py backend/tests/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full backend tests**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests -q`

Expected: PASS.

- [ ] **Step 3: Run frontend tests**

Run: `rtk npm test --prefix frontend`

Expected: PASS.

- [ ] **Step 4: Run frontend lint**

Run: `rtk npm run lint --prefix frontend`

Expected: PASS.

- [ ] **Step 5: Run frontend build**

Run: `rtk npm run build --prefix frontend`

Expected: PASS.

- [ ] **Step 6: Start backend locally**

Run:

```bash
rtk backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

Expected: FastAPI starts on `http://localhost:8000`.

- [ ] **Step 7: Start frontend locally**

Run: `rtk npm run dev --prefix frontend`

Expected: Next.js starts on `http://localhost:3000`.

---

## Self-Review

Spec coverage:

- Multi-turn conversation: Tasks 7, 8, 9, and 10.
- PostgreSQL storage: Tasks 1, 2, and 4.
- Image version history and restore: Tasks 4, 7, 8, and 10.
- Text model `gpt-5.5`: Task 6.
- Image model `gpt-image-2`: Tasks 5 and 6.
- MCP/skill future boundary: represented by the whitelisted `AgentToolRegistry` in Task 5.
- Existing one-shot image route remains: no task removes or rewrites `/api/images/generate`.

Placeholder scan:

- The plan defines concrete file paths, route paths, environment variables, model IDs, tests, and implementation snippets.
- The plan avoids dynamic tool loading and does not leave MCP or skill execution open-ended.

Type consistency:

- Backend response DTOs use camelCase names that match the frontend `AgentEnvelope`.
- Tool name is consistently `gpt_image_2_edit`.
- Model IDs are consistently `gpt-5.5` for text decisions and `gpt-image-2` for image edits.
