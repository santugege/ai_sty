# Agent Multi-Session Storage Design

Date: 2026-05-10

## Goal

Upgrade `/agent` from one in-memory conversation to a ChatGPT-style multi-session workspace. Users can create, switch, reload, and delete conversations. Each conversation is persisted, keeps its own image context, and maintains a concise summary for later turns and the session list.

## Decision

Use PostgreSQL for durable conversation metadata and MinIO for image files. Both services should run locally through Docker Desktop. This matches the existing database direction while avoiding large binary image data inside PostgreSQL.

The implementation should restore and extend the existing persistence skeleton in `backend/app/agent_models.py`, `backend/app/agent_repository.py`, `backend/app/db.py`, `backend/app/image_storage.py`, and `backend/alembic`. The current `/api/agent/conversation` path is an in-memory single-session API and should be replaced as the primary frontend path by session-scoped API routes.

## Current Context

The current `/agent` page renders `AgentImageWorkbench` from `frontend/src/components/agent-image-workbench.tsx`. It calls `sendConversationMessage()` and `resetConversation()` from `frontend/src/lib/agent-api.ts`.

The backend currently exposes:

- `POST /api/agent/conversation`
- `POST /api/agent/conversation/reset`

Those routes are wired in `backend/app/main.py` and use one process-global `ChatGptConversationService`. The service stores messages and current image bytes in dataclasses, so a backend restart loses conversation state and every browser shares the same server-side conversation.

There is already a partial database foundation:

- `AgentSessionRow`, `AgentMessageRow`, and `ImageVersionRow` in `backend/app/agent_models.py`
- `AgentRepository` in `backend/app/agent_repository.py`
- `Base`, `engine`, and `get_db_session()` in `backend/app/db.py`
- Alembic migration `backend/alembic/versions/20260508_0001_agent_tables.py`
- local image storage helper in `backend/app/image_storage.py`

## Architecture

The backend should expose session resources under `/api/agent/sessions`. Each request loads or mutates one persisted session through `AgentRepository`. The agent service should no longer own a global in-memory state. Instead, it receives a repository, object storage adapter, planner, and tool registry.

The service flow for a user turn:

1. Validate text and uploaded files.
2. Create or load the target session.
3. Store uploaded images in MinIO and persist metadata in PostgreSQL.
4. Build model context from the session summary, recent messages, current image state, and `previous_response_id`.
5. Call the existing planner in `backend/app/agent_openai.py`.
6. For answer or clarification turns, persist the assistant message and refresh session metadata.
7. For image edit turns, read the current image from MinIO, execute `gpt_image_2_edit`, store the result in MinIO, persist an `image_versions` row, and attach the generated image to the assistant message.
8. Refresh the conversation summary when the message threshold is reached.
9. Return a stable envelope containing the session, messages, current image, and summary.

## Storage

PostgreSQL owns durable metadata:

- `agent_sessions`
  - `id`
  - `title`
  - `summary`
  - `summary_updated_at`
  - `current_version_id`
  - `previous_response_id`
  - `status`
  - `created_at`
  - `updated_at`
- `agent_messages`
  - `id`
  - `session_id`
  - `role`
  - `content`
  - `response_id`
  - `tool_call_id`
  - `image_version_id`
  - `created_at`
- `image_versions`
  - `id`
  - `session_id`
  - `parent_version_id`
  - `storage_key`
  - `public_url`
  - `mime_type`
  - `width`
  - `height`
  - `prompt`
  - `revised_prompt`
  - `model`
  - `created_at`

MinIO owns binary image data:

- uploaded context images
- generated or edited result images

Use object keys such as `agent-sessions/{session_id}/{uuid}.png`. PostgreSQL stores the key and optional public URL. The first local version can serve image bytes as data URLs in API responses for compatibility with the existing frontend rendering.

## API

Primary routes:

```txt
GET    /api/agent/sessions
POST   /api/agent/sessions
GET    /api/agent/sessions/{session_id}
POST   /api/agent/sessions/{session_id}/messages
PATCH  /api/agent/sessions/{session_id}
DELETE /api/agent/sessions/{session_id}
```

Optional compatibility:

- Keep `/api/agent/conversation` temporarily only if tests or callers still require it.
- The frontend should move to the session routes.

Envelope shape:

```json
{
  "conversation": {
    "id": "uuid",
    "title": "string",
    "summary": "string or null",
    "previousResponseId": "string or null",
    "status": "active",
    "createdAt": "datetime",
    "updatedAt": "datetime"
  },
  "messages": [],
  "currentImage": null,
  "error": null
}
```

The session list should return a compact DTO with no message bodies unless needed:

```json
{
  "sessions": [
    {
      "id": "uuid",
      "title": "string",
      "summary": "string or null",
      "status": "active",
      "createdAt": "datetime",
      "updatedAt": "datetime"
    }
  ]
}
```

## Summary

Each conversation stores a rolling summary. The first implementation should be simple:

- Use the first user message as the initial title source.
- Refresh the summary after assistant responses when the conversation has at least six messages and either no summary exists or at least four messages were added since the last summary.
- Call a summary function in `backend/app/agent_openai.py`.
- If summary generation fails, log the failure but still return the normal agent response.

The planner receives:

- the current `summary`
- the last 12 messages
- current image availability
- uploaded image count
- previous response id

## Frontend

`/agent` should become a two-pane ChatGPT-style workspace:

- left session rail with new session, recent sessions, active state, and delete action
- main message panel for the selected session
- composer that sends messages to the active session
- automatic session creation when the user sends the first message without an active session
- reload support by fetching sessions on mount and loading the most recently updated session

Keep the existing image upload, size selector, current image preview, and message bubble rendering. Use valid UTF-8 Chinese UI text when touching the existing mojibake strings.

## Docker Desktop

Add a root `docker-compose.yml` with:

- `postgres`
- `minio`
- optional `minio-init` bucket creation helper

Environment variables:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/image_agent
MINIO_ENDPOINT=http://localhost:9000
MINIO_PUBLIC_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=agent-images
OPENAI_AGENT_MODEL=gpt-5.4-mini
OPENAI_IMAGE_MODEL=gpt-image-2
```

## Error Handling

- Missing session returns 404 JSON.
- Empty message with no images returns 400 JSON.
- Invalid image uploads are rejected before storage.
- MinIO failures return a storage-specific 502 JSON message.
- Summary failures are non-fatal and should be logged.
- Delete should remove database rows and attempt to remove MinIO objects; object deletion failures should be logged and should not leave a half-deleted database transaction.

## Testing

Backend:

- model tests for new columns and relationships
- repository tests for listing, loading, updating summary, message image linkage, and deletion
- storage tests using a fake S3-compatible client
- service tests for creating sessions, sending follow-ups to a specific session, preserving separate contexts, and summary refresh
- route tests for session CRUD and file upload validation

Frontend:

- API client tests that reference session routes
- workbench source tests for session list, switching, new session, delete, and session-scoped send

Verification:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
rtk powershell -NoProfile -Command "Set-Location frontend; npm test"
rtk powershell -NoProfile -Command "Set-Location frontend; npm run build"
```

## Rollout

Implement the persistence layer first, then service logic, then API routes, then frontend. Keep `/api/images/generate` unchanged. After the session API is stable, remove or de-emphasize the old reset-based in-memory workflow.
