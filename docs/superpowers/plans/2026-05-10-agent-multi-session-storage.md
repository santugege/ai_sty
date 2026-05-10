# Agent Multi-Session Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current in-memory single `/agent` conversation with ChatGPT-style persisted multi-session conversations backed by PostgreSQL and MinIO.

**Architecture:** Keep `/api/images/generate` unchanged. Convert the agent path to session-scoped FastAPI routes backed by SQLAlchemy repositories, a MinIO object storage adapter, and a stateless agent service that rebuilds context from persisted session data. The Next.js `/agent` page loads a session list, switches between sessions, and sends messages to the selected session.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, MinIO/S3-compatible storage, OpenAI Responses API, Next.js, React, Node test runner, pytest.

---

## File Structure

- Modify `backend/app/agent_models.py`: add summary fields and link assistant messages to image versions.
- Create `backend/alembic/versions/20260510_0002_agent_sessions_summary_storage.py`: migrate new columns.
- Modify `backend/app/agent_repository.py`: add session listing, summary update, title update, message image linkage, and delete helpers.
- Modify `backend/app/image_storage.py`: keep local helpers and add a MinIO/S3-compatible storage adapter behind a small interface.
- Create `backend/tests/test_minio_image_storage.py`: storage adapter unit tests with a fake client.
- Modify `backend/app/agent_schemas.py`: add list DTOs, summary fields, and image linkage fields.
- Modify `backend/app/agent_openai.py`: add summary generation function and planner summary input.
- Modify `backend/app/agent_service.py`: replace global dataclass state workflow with repository-backed session methods.
- Modify `backend/app/main.py`: wire session routes, database dependency, storage dependency, and service factory.
- Modify `backend/tests/test_agent_models.py`: assert new schema columns.
- Modify `backend/tests/test_agent_repository.py`: cover new repository methods.
- Modify `backend/tests/test_agent_service.py`: cover multi-session behavior and summary refresh with fakes.
- Modify `backend/tests/test_agent_routes.py`: switch expected routes from old single conversation API to session API.
- Modify `backend/tests/test_agent_dependencies.py`: assert MinIO env and dependency.
- Modify `backend/requirements.txt`: add `boto3`.
- Modify `backend/.env.example`: add MinIO settings and remove secrets.
- Create `docker-compose.yml`: run PostgreSQL and MinIO through Docker Desktop.
- Modify `frontend/src/lib/agent-api.ts`: add session API client functions and types.
- Modify `frontend/src/components/agent-image-workbench.tsx`: add session rail and session-scoped message flow.
- Modify `frontend/tests/agent-workbench.test.mjs`: assert session UI and API usage.

## Task 1: Database Model and Migration

**Files:**
- Modify: `backend/app/agent_models.py`
- Create: `backend/alembic/versions/20260510_0002_agent_sessions_summary_storage.py`
- Test: `backend/tests/test_agent_models.py`

- [ ] **Step 1: Write the failing model tests**

Add these tests to `backend/tests/test_agent_models.py`:

```python
def test_agent_session_summary_columns():
    assert {"summary", "summary_updated_at"} <= set(
        AgentSessionRow.__table__.columns.keys()
    )


def test_agent_message_can_reference_image_version():
    assert "image_version_id" in AgentMessageRow.__table__.columns.keys()
    assert AgentMessageRow.image_version.property.mapper.class_ is ImageVersionRow
```

- [ ] **Step 2: Run model tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_models.py -q
```

Expected: FAIL because `summary`, `summary_updated_at`, `image_version_id`, or `image_version` do not exist.

- [ ] **Step 3: Add model columns and relationship**

Modify `AgentSessionRow` in `backend/app/agent_models.py`:

```python
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

Modify `AgentMessageRow`:

```python
    image_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("image_versions.id"), nullable=True
    )
```

Add the relationship to `AgentMessageRow`:

```python
    image_version: Mapped[ImageVersionRow | None] = relationship(
        "ImageVersionRow", foreign_keys=[image_version_id]
    )
```

Keep the existing `session` relationship unchanged.

- [ ] **Step 4: Add Alembic migration**

Create `backend/alembic/versions/20260510_0002_agent_sessions_summary_storage.py`:

```python
"""add agent session summaries and message image links

Revision ID: 20260510_0002
Revises: 20260508_0001
Create Date: 2026-05-10 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0002"
down_revision = "20260508_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_sessions", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "agent_sessions",
        sa.Column("summary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_messages", sa.Column("image_version_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_agent_messages_image_version_id_image_versions",
        "agent_messages",
        "image_versions",
        ["image_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agent_messages_image_version_id_image_versions",
        "agent_messages",
        type_="foreignkey",
    )
    op.drop_column("agent_messages", "image_version_id")
    op.drop_column("agent_sessions", "summary_updated_at")
    op.drop_column("agent_sessions", "summary")
```

- [ ] **Step 5: Run model tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_models.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/agent_models.py backend/alembic/versions/20260510_0002_agent_sessions_summary_storage.py backend/tests/test_agent_models.py
rtk git commit -m "feat: extend agent session schema"
```

## Task 2: Repository Session Operations

**Files:**
- Modify: `backend/app/agent_repository.py`
- Test: `backend/tests/test_agent_repository.py`

- [ ] **Step 1: Write failing repository tests**

Add these tests to `backend/tests/test_agent_repository.py`:

```python
def test_list_sessions_orders_by_recent_update():
    repo = make_repo()
    first = repo.create_session("First")
    second = repo.create_session("Second")

    sessions = repo.list_sessions()

    assert [row.id for row in sessions] == [second.id, first.id]


def test_update_session_summary_persists_text_and_timestamp():
    repo = make_repo()
    session = repo.create_session("Summary test")

    repo.update_session_summary(session.id, "User wants a clean product image.")

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.summary == "User wants a clean product image."
    assert state.session.summary_updated_at is not None


def test_add_message_can_link_generated_image_version():
    repo = make_repo()
    session = repo.create_session("Linked image")
    version = repo.add_image_version(
        session_id=session.id,
        parent_version_id=None,
        storage_key="agent-sessions/session/v1.png",
        mime_type="image/png",
        prompt="edit",
        model="gpt-image-2",
    )

    message = repo.add_message(
        session_id=session.id,
        role="assistant",
        content="Done.",
        image_version_id=version.id,
    )

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.messages == [message]
    assert state.messages[0].image_version_id == version.id


def test_update_session_title_renames_existing_session():
    repo = make_repo()
    session = repo.create_session("Old")

    repo.update_session_title(session.id, "New")

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.title == "New"
```

- [ ] **Step 2: Run repository tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_repository.py -q
```

Expected: FAIL because `list_sessions`, `update_session_summary`, `update_session_title`, or `image_version_id` support is missing.

- [ ] **Step 3: Implement repository methods**

Modify imports in `backend/app/agent_repository.py`:

```python
from datetime import timezone, datetime
```

Change `add_message` signature:

```python
    def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        response_id: str | None = None,
        tool_call_id: str | None = None,
        image_version_id: uuid.UUID | None = None,
    ) -> AgentMessageRow:
```

Add `image_version_id=image_version_id` to `AgentMessageRow(...)`.

Add these methods to `AgentRepository`:

```python
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
```

- [ ] **Step 4: Run repository tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_repository.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/agent_repository.py backend/tests/test_agent_repository.py
rtk git commit -m "feat: add agent session repository operations"
```

## Task 3: MinIO Object Storage Adapter

**Files:**
- Modify: `backend/app/image_storage.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Modify: `backend/tests/test_agent_dependencies.py`
- Create: `backend/tests/test_minio_image_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `backend/tests/test_minio_image_storage.py`:

```python
from app.image_storage import MinioImageStorage


class FakeS3Client:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[(Bucket, Key)] = {
            "body": Body,
            "content_type": ContentType,
        }

    def get_object(self, Bucket, Key):
        class Body:
            def read(self_inner):
                return self.objects[(Bucket, Key)]["body"]

        return {"Body": Body()}

    def delete_object(self, Bucket, Key):
        self.deleted.append((Bucket, Key))


def test_minio_storage_writes_reads_and_deletes_image():
    client = FakeS3Client()
    storage = MinioImageStorage(
        bucket="agent-images",
        client=client,
        public_endpoint="http://localhost:9000",
    )

    stored = storage.write_image(
        b"image-bytes",
        mime_type="image/png",
        prefix="agent-sessions/session-1",
    )

    assert stored.storage_key.startswith("agent-sessions/session-1/")
    assert stored.public_url == f"http://localhost:9000/agent-images/{stored.storage_key}"
    assert storage.read_image(stored.storage_key) == b"image-bytes"

    storage.delete_image(stored.storage_key)

    assert client.deleted == [("agent-images", stored.storage_key)]
```

Modify `backend/tests/test_agent_dependencies.py`:

```python
def test_backend_dependencies_include_minio_storage_stack():
    requirements = Path("backend/requirements.txt").read_text(encoding="utf-8")
    env_example = Path("backend/.env.example").read_text(encoding="utf-8")

    assert "boto3" in requirements
    assert "MINIO_ENDPOINT=" in env_example
    assert "MINIO_BUCKET=" in env_example
    assert "MINIO_ACCESS_KEY=" in env_example
    assert "MINIO_SECRET_KEY=" in env_example
```

- [ ] **Step 2: Run storage tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_minio_image_storage.py backend/tests/test_agent_dependencies.py -q
```

Expected: FAIL because `MinioImageStorage`, `boto3`, and MinIO env values are missing.

- [ ] **Step 3: Add dependency and env settings**

Append to `backend/requirements.txt`:

```txt
boto3
```

Update `backend/.env.example` to use non-secret sample values:

```env
OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_AGENT_MODEL=gpt-5.4-mini
FRONTEND_ORIGIN=http://localhost:3000
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/image_agent
MINIO_ENDPOINT=http://localhost:9000
MINIO_PUBLIC_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=agent-images
```

- [ ] **Step 4: Implement MinIO storage**

Add to `backend/app/image_storage.py`:

```python
from urllib.parse import quote


class MinioImageStorage:
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        public_endpoint: str | None = None,
        client=None,
    ) -> None:
        self.bucket = bucket
        self.public_endpoint = (public_endpoint or endpoint_url or "").rstrip("/")
        if client is not None:
            self.client = client
            return

        import boto3

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def write_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prefix: str = "agent-sessions",
    ) -> StoredImage:
        normalized_prefix = prefix.strip("/").replace("\\", "/")
        storage_key = f"{normalized_prefix}/{uuid.uuid4()}{extension_for_mime_type(mime_type)}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=storage_key,
            Body=image_bytes,
            ContentType=mime_type,
        )
        public_url = None
        if self.public_endpoint:
            public_url = (
                f"{self.public_endpoint}/{quote(self.bucket)}/{quote(storage_key)}"
            )
        return StoredImage(
            storage_key=storage_key,
            mime_type=mime_type,
            public_url=public_url,
        )

    def read_image(self, storage_key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=storage_key)
        return response["Body"].read()

    def delete_image(self, storage_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=storage_key)
```

- [ ] **Step 5: Run storage tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_minio_image_storage.py backend/tests/test_agent_dependencies.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/image_storage.py backend/requirements.txt backend/.env.example backend/tests/test_minio_image_storage.py backend/tests/test_agent_dependencies.py
rtk git commit -m "feat: add minio image storage"
```

## Task 4: Agent DTOs and Summary API Helpers

**Files:**
- Modify: `backend/app/agent_schemas.py`
- Modify: `backend/app/agent_openai.py`
- Test: `backend/tests/test_agent_openai.py`

- [ ] **Step 1: Write failing DTO and summary tests**

Add to `backend/tests/test_agent_openai.py`:

```python
def test_request_conversation_summary_returns_output_text():
    calls = []

    class FakeResponse:
        output_text = "User wants a bright product image with clean background."

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return FakeResponse()

    class FakeClient:
        def __init__(self, **kwargs):
            self.responses = FakeResponses()

    from app.agent_openai import request_conversation_summary

    summary = request_conversation_summary(
        api_key="sk-test",
        agent_model="gpt-5.4-mini",
        previous_summary=None,
        recent_messages=[
            {"role": "user", "content": "Make it brighter."},
            {"role": "assistant", "content": "Done."},
        ],
        client_factory=FakeClient,
    )

    assert summary == "User wants a bright product image with clean background."
    assert calls[0]["model"] == "gpt-5.4-mini"
```

- [ ] **Step 2: Run summary tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_openai.py -q
```

Expected: FAIL because `request_conversation_summary` does not exist.

- [ ] **Step 3: Extend schemas**

Modify `ConversationDto` in `backend/app/agent_schemas.py`:

```python
class ConversationDto(BaseModel):
    id: str
    title: str
    summary: str | None = None
    previousResponseId: str | None
    status: str
    createdAt: datetime
    updatedAt: datetime
```

Modify `ConversationMessageDto`:

```python
    imageVersionId: str | None = None
```

Add:

```python
class ConversationListItemDto(BaseModel):
    id: str
    title: str
    summary: str | None = None
    status: str
    createdAt: datetime
    updatedAt: datetime


class ConversationListEnvelope(BaseModel):
    sessions: list[ConversationListItemDto]
```

- [ ] **Step 4: Implement summary helper**

Add to `backend/app/agent_openai.py`:

```python
def request_conversation_summary(
    api_key: str,
    agent_model: str,
    previous_summary: str | None,
    recent_messages: list[dict[str, str]],
    base_url: str | None = None,
    client_factory: type[Any] = OpenAI,
) -> str:
    client = client_factory(**openai_client_kwargs(api_key, base_url))
    response = client.responses.create(
        model=agent_model,
        input=[
            {
                "role": "system",
                "content": (
                    "Summarize this image editing conversation for future context. "
                    "Keep stable user preferences, current goal, visual constraints, "
                    "and unresolved questions. Return only the summary text."
                ),
            },
            {
                "role": "user",
                "content": {
                    "previous_summary": previous_summary or "",
                    "recent_messages": recent_messages,
                },
            },
        ],
    )
    return str(response.output_text).strip()
```

- [ ] **Step 5: Run summary tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_openai.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/agent_schemas.py backend/app/agent_openai.py backend/tests/test_agent_openai.py
rtk git commit -m "feat: add agent summary DTOs"
```

## Task 5: Repository-Backed Agent Service

**Files:**
- Modify: `backend/app/agent_service.py`
- Test: `backend/tests/test_agent_service.py`

- [ ] **Step 1: Write failing multi-session service tests**

Replace the old single in-memory assumptions in `backend/tests/test_agent_service.py` with tests that construct the service with an in-memory SQLite repository and fake storage. Start with these three tests:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent_repository import AgentRepository
from app.db import Base


class FakeStorage:
    def __init__(self):
        self.objects = {}

    def write_image(self, image_bytes, mime_type="image/png", prefix="agent-sessions"):
        from app.image_storage import StoredImage
        key = f"{prefix}/image-{len(self.objects) + 1}.png"
        self.objects[key] = image_bytes
        return StoredImage(storage_key=key, mime_type=mime_type, public_url=None)

    def read_image(self, storage_key):
        return self.objects[storage_key]

    def delete_image(self, storage_key):
        self.objects.pop(storage_key, None)


def make_persistent_service(decision, summary_result=None):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repo = AgentRepository(Session(engine))
    storage = FakeStorage()
    planner_calls = []
    summary_calls = []

    def fake_planner(**kwargs):
        planner_calls.append(kwargs)
        return decision

    def fake_summarizer(**kwargs):
        summary_calls.append(kwargs)
        return summary_result or "Session summary"

    service = ChatGptConversationService(
        planner=fake_planner,
        tools={"gpt_image_2_edit": FakeTool()},
        repo=repo,
        storage=storage,
        summarizer=fake_summarizer,
    )
    return service, repo, storage, planner_calls, summary_calls


def test_create_session_persists_conversation_and_uploaded_image():
    service, repo, storage, _planner_calls, _summary_calls = make_persistent_service(
        ConversationTurnDecision(
            action="answer",
            assistant_message="I can edit this image.",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_1",
        )
    )

    envelope = service.create_session(
        message="Make this image cleaner.",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    state = repo.get_session_state(envelope.conversation.id)
    assert state is not None
    assert [message.role for message in state.messages] == ["user", "assistant"]
    assert len(storage.objects) == 1
    assert envelope.currentImage is not None


def test_sessions_keep_separate_previous_response_ids():
    first, repo, _storage, _planner_calls, _summary_calls = make_persistent_service(
        ConversationTurnDecision("answer", "First", None, None, "resp_first")
    )
    first_envelope = first.create_session("First request", [], "1536x1024")

    second = ChatGptConversationService(
        planner=lambda **kwargs: ConversationTurnDecision(
            "answer", "Second", None, None, "resp_second"
        ),
        tools={"gpt_image_2_edit": FakeTool()},
        repo=repo,
        storage=_storage,
    )
    second_envelope = second.create_session("Second request", [], "1536x1024")

    assert repo.get_session_state(first_envelope.conversation.id).session.previous_response_id == "resp_first"
    assert repo.get_session_state(second_envelope.conversation.id).session.previous_response_id == "resp_second"


def test_send_message_uses_target_session_summary_and_recent_messages():
    service, repo, _storage, planner_calls, _summary_calls = make_persistent_service(
        ConversationTurnDecision("answer", "First", None, None, "resp_1")
    )
    created = service.create_session("Start", [], "1536x1024")
    repo.update_session_summary(created.conversation.id, "Existing summary")

    service.planner = lambda **kwargs: ConversationTurnDecision(
        "answer", "Follow-up", None, None, "resp_2"
    )
    service.send_message(created.conversation.id, "Continue", [], "1536x1024")

    assert planner_calls[-1]["summary"] == "Existing summary"
    assert planner_calls[-1]["previous_response_id"] == "resp_1"
```

- [ ] **Step 2: Run service tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_service.py -q
```

Expected: FAIL because `ChatGptConversationService` does not accept `repo`, `storage`, or `summarizer`, and `create_session` is missing.

- [ ] **Step 3: Update service constructor**

Modify `ChatGptConversationService.__init__` in `backend/app/agent_service.py`:

```python
    def __init__(
        self,
        planner: Planner,
        tools: dict[str, AgentTool],
        repo: AgentRepository | None = None,
        storage: object | None = None,
        summarizer: Callable[..., str] | None = None,
        state: ConversationState | None = None,
    ) -> None:
        self.planner = planner
        self.tools = tools
        self.repo = repo
        self.storage = storage
        self.summarizer = summarizer
        self.state = state or ConversationState()
```

Keep the old in-memory `send_message` path temporarily when `self.repo is None`.

- [ ] **Step 4: Add persistent methods**

Add methods to `ChatGptConversationService`:

```python
    def create_session(
        self,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
    ) -> AgentEnvelope:
        if self.repo is None or self.storage is None:
            return self.send_message(message, attachments, size)

        title = _title_from_message(message)
        session = self.repo.create_session(title=title)
        return self.send_message(str(session.id), message, attachments, size)

    def send_session_message(
        self,
        session_id: str,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
    ) -> AgentEnvelope:
        return self.send_message(session_id, message, attachments, size)
```

Then change `send_message` to dispatch based on arguments by introducing a new persistent helper:

```python
    def send_message(self, *args, **kwargs) -> AgentEnvelope:
        if self.repo is None:
            return self._send_in_memory_message(*args, **kwargs)

        if len(args) >= 4:
            session_id, message, attachments, size = args[:4]
        else:
            session_id = kwargs["session_id"]
            message = kwargs["message"]
            attachments = kwargs["attachments"]
            size = kwargs["size"]
        return self._send_persistent_message(session_id, message, attachments, size)
```

Rename the old method body to `_send_in_memory_message`.

Implement `_send_persistent_message`:

```python
    def _send_persistent_message(
        self,
        session_id: str,
        message: str,
        attachments: list[dict[str, object]],
        size: str,
    ) -> AgentEnvelope:
        normalized_message = message.strip()
        if not normalized_message and not attachments:
            raise ConversationInputError("Please enter a message or upload an image.")

        parsed_session_id = uuid.UUID(str(session_id))
        state = self.repo.get_session_state(parsed_session_id)
        if state is None:
            raise ConversationInputError("Conversation not found.")

        uploaded_version = None
        for attachment in attachments:
            stored = self.storage.write_image(
                bytes(attachment["image_bytes"]),
                mime_type=str(attachment["mime_type"]),
                prefix=f"agent-sessions/{parsed_session_id}",
            )
            uploaded_version = self.repo.add_image_version(
                session_id=parsed_session_id,
                parent_version_id=state.session.current_version_id,
                storage_key=stored.storage_key,
                public_url=stored.public_url,
                mime_type=stored.mime_type,
                prompt=normalized_message or "Uploaded image",
                model="user-upload",
            )
            self.repo.set_current_version(parsed_session_id, uploaded_version.id)

        self.repo.add_message(parsed_session_id, "user", normalized_message)
        state = self.repo.get_session_state(parsed_session_id)
        current_version = _current_version(state)
        decision = self.planner(
            user_message=normalized_message,
            summary=state.session.summary,
            recent_messages=[
                {"role": item.role, "content": item.content}
                for item in state.messages[-12:]
            ],
            has_current_image=current_version is not None,
            uploaded_image_count=len(attachments),
            previous_response_id=state.session.previous_response_id,
        )

        if decision.action in {"answer", "clarify"}:
            self.repo.add_message(
                parsed_session_id,
                "assistant",
                decision.assistant_message,
                response_id=decision.response_id,
            )
            self.repo.set_previous_response_id(parsed_session_id, decision.response_id)
            self._maybe_refresh_summary(parsed_session_id)
            return self.get_session(parsed_session_id)

        if current_version is None:
            raise ConversationInputError("Please upload an image first.")

        tool = self.tools.get(decision.tool_name or "")
        if tool is None:
            raise AgentServiceError("The selected agent tool is not available.")

        source_bytes = self.storage.read_image(current_version.storage_key)
        result = tool.execute(
            AgentToolContext(
                image_bytes=source_bytes,
                image_name="current-image.png",
                mime_type=current_version.mime_type,
                instruction=decision.tool_instruction or "",
                size=size,
            )
        )
        stored = self.storage.write_image(
            result.image_bytes,
            mime_type=result.mime_type,
            prefix=f"agent-sessions/{parsed_session_id}",
        )
        generated_version = self.repo.add_image_version(
            session_id=parsed_session_id,
            parent_version_id=current_version.id,
            storage_key=stored.storage_key,
            public_url=stored.public_url,
            mime_type=stored.mime_type,
            prompt=result.prompt,
            revised_prompt=result.revised_prompt,
            model=result.model,
        )
        self.repo.set_current_version(parsed_session_id, generated_version.id)
        self.repo.add_message(
            parsed_session_id,
            "assistant",
            decision.assistant_message,
            response_id=decision.response_id,
            image_version_id=generated_version.id,
        )
        self.repo.set_previous_response_id(parsed_session_id, decision.response_id)
        self._maybe_refresh_summary(parsed_session_id)
        return self.get_session(parsed_session_id)
```

Add helper functions:

```python
def _title_from_message(message: str) -> str:
    normalized = message.strip()
    return (normalized[:60] or "New conversation")


def _current_version(state: AgentSessionState | None) -> ImageVersionRow | None:
    if state is None or state.session.current_version_id is None:
        return None
    for version in state.versions:
        if version.id == state.session.current_version_id:
            return version
    return None
```

- [ ] **Step 5: Add session envelope methods**

Add to `ChatGptConversationService`:

```python
    def list_sessions(self) -> ConversationListEnvelope:
        return ConversationListEnvelope(
            sessions=[
                ConversationListItemDto(
                    id=str(session.id),
                    title=session.title,
                    summary=session.summary,
                    status=session.status,
                    createdAt=session.created_at,
                    updatedAt=session.updated_at,
                )
                for session in self.repo.list_sessions()
            ]
        )

    def get_session(self, session_id: str | uuid.UUID) -> AgentEnvelope:
        state = self.repo.get_session_state(uuid.UUID(str(session_id)))
        if state is None:
            raise ConversationInputError("Conversation not found.")
        return self._persistent_envelope(state)
```

Implement `_persistent_envelope` using existing `_data_url`:

```python
    def _persistent_envelope(self, state: AgentSessionState) -> AgentEnvelope:
        versions_by_id = {version.id: version for version in state.versions}
        current_version = _current_version(state)
        return AgentEnvelope(
            conversation=ConversationDto(
                id=str(state.session.id),
                title=state.session.title,
                summary=state.session.summary,
                previousResponseId=state.session.previous_response_id,
                status=state.session.status,
                createdAt=state.session.created_at,
                updatedAt=state.session.updated_at,
            ),
            messages=[
                ConversationMessageDto(
                    id=str(message.id),
                    role=message.role,
                    content=message.content,
                    attachments=[],
                    responseId=message.response_id,
                    imageVersionId=(
                        str(message.image_version_id)
                        if message.image_version_id is not None
                        else None
                    ),
                    image=self._version_image_dto(versions_by_id.get(message.image_version_id)),
                    createdAt=message.created_at,
                )
                for message in state.messages
            ],
            currentImage=self._version_image_dto(current_version),
            error=None,
        )
```

Add `_version_image_dto`:

```python
    def _version_image_dto(self, version: ImageVersionRow | None) -> ConversationImageDto | None:
        if version is None:
            return None
        return ConversationImageDto(
            id=str(version.id),
            src=_data_url(self.storage.read_image(version.storage_key), version.mime_type),
            mimeType=version.mime_type,
            prompt=version.prompt,
            revisedPrompt=version.revised_prompt,
            model=version.model,
            createdAt=version.created_at,
        )
```

- [ ] **Step 6: Add summary refresh**

Add:

```python
    def _maybe_refresh_summary(self, session_id: uuid.UUID) -> None:
        if self.summarizer is None:
            return
        state = self.repo.get_session_state(session_id)
        if state is None or len(state.messages) < 6:
            return
        try:
            summary = self.summarizer(
                previous_summary=state.session.summary,
                recent_messages=[
                    {"role": item.role, "content": item.content}
                    for item in state.messages[-12:]
                ],
            )
        except Exception:
            return
        if summary:
            self.repo.update_session_summary(session_id, summary)
```

- [ ] **Step 7: Run service tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_service.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
rtk git add backend/app/agent_service.py backend/tests/test_agent_service.py
rtk git commit -m "feat: persist agent session turns"
```

## Task 6: Session API Routes

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_agent_routes.py`

- [ ] **Step 1: Write failing route tests**

Replace `test_conversation_routes_exist` in `backend/tests/test_agent_routes.py` with:

```python
def test_agent_session_routes_exist():
    routes = {route.path for route in app.routes}

    assert "/api/agent/sessions" in routes
    assert "/api/agent/sessions/{session_id}" in routes
    assert "/api/agent/sessions/{session_id}/messages" in routes
```

Add:

```python
def test_create_session_accepts_text_and_image_attachment(monkeypatch):
    class FakeEnvelope:
        def model_dump(self, mode):
            return {"conversation": {"id": "session-1"}, "messages": []}

    class FakeService:
        def create_session(self, message, attachments, size):
            assert message == "Make it white."
            assert size == "1536x1024"
            assert attachments[0]["image_bytes"] == TINY_PNG
            return FakeEnvelope()

    monkeypatch.setattr("app.main.build_agent_service", lambda db=None: FakeService())

    response = client.post(
        "/api/agent/sessions",
        data={"message": "Make it white.", "size": "1536x1024"},
        files={"images": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["conversation"]["id"] == "session-1"


def test_send_session_message_uses_session_id(monkeypatch):
    class FakeEnvelope:
        def model_dump(self, mode):
            return {"ok": True}

    class FakeService:
        def send_message(self, session_id, message, attachments, size):
            assert str(session_id) == "00000000-0000-0000-0000-000000000001"
            assert message == "Brighter."
            return FakeEnvelope()

    monkeypatch.setattr("app.main.build_agent_service", lambda db=None: FakeService())

    response = client.post(
        "/api/agent/sessions/00000000-0000-0000-0000-000000000001/messages",
        data={"message": "Brighter.", "size": "1536x1024"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
```

- [ ] **Step 2: Run route tests red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_routes.py -q
```

Expected: FAIL because session routes and `build_agent_service` are missing.

- [ ] **Step 3: Wire service factory**

In `backend/app/main.py`, import:

```python
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from app.agent_openai import request_conversation_summary
from app.agent_repository import AgentRepository
from app.db import get_db_session
from app.image_storage import MinioImageStorage
```

Add:

```python
def build_image_storage() -> MinioImageStorage:
    return MinioImageStorage(
        bucket=os.getenv("MINIO_BUCKET", "agent-images"),
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        public_endpoint=os.getenv("MINIO_PUBLIC_ENDPOINT", os.getenv("MINIO_ENDPOINT", "")),
    )


def build_agent_service(db: Session | None = None) -> ChatGptConversationService:
    api_key = os.getenv("OPENAI_API_KEY") or ""
    image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    agent_model = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.4-mini")
    base_url = openai_base_url()
    image_client = create_openai_image_client(
        api_key=api_key,
        image_model=image_model,
        base_url=base_url,
    )

    def planner(**kwargs):
        return request_conversation_turn(
            api_key=api_key,
            agent_model=agent_model,
            base_url=base_url,
            **kwargs,
        )

    def summarizer(**kwargs):
        return request_conversation_summary(
            api_key=api_key,
            agent_model=agent_model,
            base_url=base_url,
            **kwargs,
        )

    return ChatGptConversationService(
        planner=planner,
        tools={"gpt_image_2_edit": GptImage2EditTool(image_client=image_client, image_model=image_model)},
        repo=AgentRepository(db),
        storage=build_image_storage(),
        summarizer=summarizer,
    )
```

- [ ] **Step 4: Add routes**

Add to `backend/app/main.py`:

```python
@app.get("/api/agent/sessions")
def list_agent_sessions(db: Session = Depends(get_db_session)):
    try:
        return build_agent_service(db).list_sessions().model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/agent/sessions")
async def create_agent_session(
    message: str = Form(""),
    size: str = Form("1536x1024"),
    images: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db_session),
):
    try:
        attachments = await read_conversation_uploads(images)
        envelope = await run_in_threadpool(
            build_agent_service(db).create_session,
            message,
            attachments,
            size,
        )
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.get("/api/agent/sessions/{session_id}")
def get_agent_session(session_id: UUID, db: Session = Depends(get_db_session)):
    try:
        return build_agent_service(db).get_session(session_id).model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)


@app.post("/api/agent/sessions/{session_id}/messages")
async def send_agent_session_message(
    session_id: UUID,
    message: str = Form(""),
    size: str = Form("1536x1024"),
    images: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db_session),
):
    try:
        attachments = await read_conversation_uploads(images)
        envelope = await run_in_threadpool(
            build_agent_service(db).send_message,
            session_id,
            message,
            attachments,
            size,
        )
        return envelope.model_dump(mode="json")
    except (AgentInputError, AgentServiceError, Exception) as error:
        return agent_error_response(error)
```

- [ ] **Step 5: Run route tests green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/main.py backend/tests/test_agent_routes.py
rtk git commit -m "feat: add agent session api routes"
```

## Task 7: Docker Desktop Services

**Files:**
- Create: `docker-compose.yml`
- Test: `backend/tests/test_agent_dependencies.py`

- [ ] **Step 1: Write failing compose test**

Add to `backend/tests/test_agent_dependencies.py`:

```python
def test_docker_compose_defines_postgres_and_minio():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "postgres:" in compose
    assert "minio:" in compose
    assert "9000:9000" in compose
    assert "5432:5432" in compose
```

- [ ] **Step 2: Run compose test red**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_dependencies.py -q
```

Expected: FAIL because `docker-compose.yml` does not exist.

- [ ] **Step 3: Add Docker Compose**

Create `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:16
    container_name: ai_sty_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: image_agent
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio:latest
    container_name: ai_sty_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

  minio-init:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 minioadmin minioadmin &&
      mc mb --ignore-existing local/agent-images
      "

volumes:
  postgres_data:
  minio_data:
```

- [ ] **Step 4: Run compose test green**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_agent_dependencies.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add docker-compose.yml backend/tests/test_agent_dependencies.py
rtk git commit -m "chore: add docker desktop storage services"
```

## Task 8: Frontend Session API Client

**Files:**
- Modify: `frontend/src/lib/agent-api.ts`
- Test: `frontend/tests/agent-workbench.test.mjs`

- [ ] **Step 1: Write failing frontend API source test**

Add to `frontend/tests/agent-workbench.test.mjs`:

```javascript
test("agent api client uses persisted session routes", () => {
  const source = readFileSync("src/lib/agent-api.ts", "utf8");

  assert.match(source, /listAgentSessions/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /getAgentSession/);
  assert.match(source, /sendAgentSessionMessage/);
  assert.match(source, /\/api\/agent\/sessions/);
});
```

- [ ] **Step 2: Run frontend tests red**

Run:

```bash
rtk powershell -NoProfile -Command "Set-Location frontend; npm test"
```

Expected: FAIL because the client still only exports `sendConversationMessage` and `resetConversation`.

- [ ] **Step 3: Update API client**

Modify `frontend/src/lib/agent-api.ts`:

```typescript
export type ConversationListItem = {
  id: string;
  title: string;
  summary?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type ConversationListEnvelope = {
  sessions: ConversationListItem[];
};
```

Add `summary` to `AgentEnvelope.conversation`.

Add functions:

```typescript
export async function listAgentSessions(): Promise<ConversationListEnvelope> {
  return readJsonResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions`, { method: "GET" }),
  );
}

export async function createAgentSession(formData: FormData) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions`, {
      method: "POST",
      body: formData,
    }),
  );
}

export async function getAgentSession(sessionId: string) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions/${sessionId}`, {
      method: "GET",
    }),
  );
}

export async function sendAgentSessionMessage(
  sessionId: string,
  formData: FormData,
) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions/${sessionId}/messages`, {
      method: "POST",
      body: formData,
    }),
  );
}

async function readJsonResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & { error?: string };
  if (!response.ok || "error" in payload) {
    throw new Error(payload.error || "Agent request failed.");
  }
  return payload;
}
```

Change `readAgentResponse` to call `readJsonResponse<AgentEnvelope>(response)`.

- [ ] **Step 4: Run frontend tests green**

Run:

```bash
rtk powershell -NoProfile -Command "Set-Location frontend; npm test"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add frontend/src/lib/agent-api.ts frontend/tests/agent-workbench.test.mjs
rtk git commit -m "feat: add frontend agent session api"
```

## Task 9: Frontend Multi-Session Workbench

**Files:**
- Modify: `frontend/src/components/agent-image-workbench.tsx`
- Test: `frontend/tests/agent-workbench.test.mjs`

- [ ] **Step 1: Write failing workbench source test**

Add to `frontend/tests/agent-workbench.test.mjs`:

```javascript
test("agent workbench renders session list and sends to active session", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /listAgentSessions/);
  assert.match(source, /getAgentSession/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /sendAgentSessionMessage/);
  assert.match(source, /sessions\.map/);
  assert.match(source, /activeSessionId/);
  assert.match(source, /New conversation|新会话/);
});
```

- [ ] **Step 2: Run frontend tests red**

Run:

```bash
rtk powershell -NoProfile -Command "Set-Location frontend; npm test"
```

Expected: FAIL because session state and UI do not exist.

- [ ] **Step 3: Update imports and state**

In `frontend/src/components/agent-image-workbench.tsx`, replace old API imports with:

```typescript
import {
  createAgentSession,
  getAgentSession,
  listAgentSessions,
  sendAgentSessionMessage,
  type AgentEnvelope,
  type ConversationImage,
  type ConversationListItem,
  type ConversationMessage,
} from "@/lib/agent-api";
```

Add React import for `useEffect`:

```typescript
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
```

Add state:

```typescript
const [sessions, setSessions] = useState<ConversationListItem[]>([]);
const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
const [isLoadingSessions, setIsLoadingSessions] = useState(true);
```

- [ ] **Step 4: Add session loading helpers**

Add inside `AgentImageWorkbench`:

```typescript
async function refreshSessions(nextActiveId?: string) {
  const envelope = await listAgentSessions();
  setSessions(envelope.sessions);
  const resolvedActiveId = nextActiveId ?? envelope.sessions[0]?.id ?? null;
  setActiveSessionId(resolvedActiveId);
  if (resolvedActiveId) {
    applyEnvelope(await getAgentSession(resolvedActiveId));
  }
}

useEffect(() => {
  let isMounted = true;
  listAgentSessions()
    .then(async (envelope) => {
      if (!isMounted) return;
      setSessions(envelope.sessions);
      const firstSession = envelope.sessions[0];
      if (firstSession) {
        setActiveSessionId(firstSession.id);
        applyEnvelope(await getAgentSession(firstSession.id));
      }
    })
    .catch((caught) => {
      if (isMounted) {
        setError(caught instanceof Error ? caught.message : "加载会话失败。");
      }
    })
    .finally(() => {
      if (isMounted) {
        setIsLoadingSessions(false);
      }
    });
  return () => {
    isMounted = false;
  };
}, []);
```

Add:

```typescript
async function handleSelectSession(sessionId: string) {
  setError("");
  setActiveSessionId(sessionId);
  setIsSubmitting(true);
  try {
    applyEnvelope(await getAgentSession(sessionId));
  } catch (caught) {
    setError(caught instanceof Error ? caught.message : "加载会话失败。");
  } finally {
    setIsSubmitting(false);
  }
}

function handleNewSession() {
  setActiveSessionId(null);
  setMessages([]);
  setCurrentImage(null);
  setMessage("");
  setError("");
}
```

- [ ] **Step 5: Send create or follow-up based on active session**

Replace the API call in `handleSubmit`:

```typescript
const envelope = activeSessionId
  ? await sendAgentSessionMessage(activeSessionId, formData)
  : await createAgentSession(formData);
```

After `applyEnvelope(envelope);`, add:

```typescript
setActiveSessionId(envelope.conversation.id);
await refreshSessions(envelope.conversation.id);
```

Replace `handleReset` with `handleNewSession` for the header button.

- [ ] **Step 6: Render session rail**

Change the root layout to a grid with an aside:

```tsx
<main className="min-h-screen bg-[#f7f7f4] text-[#171717]">
  <div className="grid min-h-screen lg:grid-cols-[18rem_minmax(0,1fr)]">
    <aside className="border-r border-[#deded8] bg-white px-3 py-4">
      <button
        type="button"
        onClick={handleNewSession}
        className="mb-3 flex h-10 w-full items-center justify-center gap-2 rounded-md border border-[#d2d2cc] text-sm font-medium"
      >
        <Plus aria-hidden="true" className="h-4 w-4" />
        新会话
      </button>
      <div className="grid gap-1">
        {sessions.map((session) => (
          <button
            key={session.id}
            type="button"
            onClick={() => void handleSelectSession(session.id)}
            className={`rounded-md px-3 py-2 text-left text-sm ${
              activeSessionId === session.id ? "bg-[#ededdf]" : "hover:bg-[#f3f3ed]"
            }`}
          >
            <span className="block truncate font-medium">{session.title}</span>
            {session.summary && (
              <span className="mt-1 line-clamp-2 block text-xs text-[#6f6f68]">
                {session.summary}
              </span>
            )}
          </button>
        ))}
        {!isLoadingSessions && sessions.length === 0 && (
          <p className="px-3 py-4 text-sm text-[#6f6f68]">暂无会话</p>
        )}
      </div>
    </aside>
    <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-4 sm:px-6">
      ...
    </div>
  </div>
</main>
```

Preserve the existing message list, current image, error, and composer inside the right column.

- [ ] **Step 7: Run frontend tests green**

Run:

```bash
rtk powershell -NoProfile -Command "Set-Location frontend; npm test"
```

Expected: PASS.

- [ ] **Step 8: Run frontend build**

Run:

```bash
rtk powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
rtk git add frontend/src/components/agent-image-workbench.tsx frontend/tests/agent-workbench.test.mjs
rtk git commit -m "feat: add multi-session agent workbench"
```

## Task 10: Final Verification

**Files:**
- No new files. Verify all touched files.

- [ ] **Step 1: Run backend tests**

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

```bash
rtk powershell -NoProfile -Command "Set-Location frontend; npm test"
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

```bash
rtk powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

Expected: PASS.

- [ ] **Step 4: Smoke Docker services**

```bash
rtk docker compose up -d postgres minio minio-init
rtk docker compose ps
```

Expected: `postgres` and `minio` are running.

- [ ] **Step 5: Apply migrations**

```bash
rtk powershell -NoProfile -Command "Set-Location backend; ..\\.venv\\Scripts\\alembic upgrade head"
```

Expected: Alembic upgrades to `20260510_0002`.

- [ ] **Step 6: Review git status**

```bash
rtk git status --short
```

Expected: no uncommitted changes, or only intentional runtime files ignored by `.gitignore`.

## Self-Review

Spec coverage:

- Multi-session conversations: Tasks 2, 5, 6, 8, and 9.
- Persistent storage: Tasks 1, 2, 3, 6, and 7.
- Per-conversation summaries: Tasks 1, 2, 4, and 5.
- ChatGPT-like frontend session switching: Tasks 8 and 9.
- Docker Desktop storage services: Task 7.
- Existing one-shot image route remains unchanged: no task modifies `/api/images/generate`.

Placeholder scan:

- The plan names concrete files, commands, routes, DTOs, and code blocks.
- The plan avoids open-ended storage or summary work; MinIO and PostgreSQL are explicit.

Type consistency:

- Backend DTO fields use `summary`, `imageVersionId`, and existing camelCase response conventions.
- Repository methods use UUID objects internally and route/service inputs convert string IDs to UUID.
