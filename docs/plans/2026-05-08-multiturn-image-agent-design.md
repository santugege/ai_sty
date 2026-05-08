# Multiturn Image Agent Design

Date: 2026-05-08

## Goal

Add an agent-driven image workflow where users can keep editing the same product image through a multi-turn conversation. The agent should understand the user's latest request, preserve the current image context, decide whether to ask a clarifying question or call an image tool, and create a versioned image history that users can restore from.

## Decision

Use a lightweight backend agent service as the first implementation. The service will call the OpenAI Responses API with `gpt-5.5` as the text agent model. Image editing is exposed to that agent as a custom `gpt_image_2_edit` tool, and that tool calls the OpenAI Images API with `gpt-image-2`.

The first real agent tool is `gpt_image_2_edit`. It wraps the OpenAI image edit path and is registered through an internal tool registry. MCP tools and local skills are future adapters on the same registry, not dynamic user-installed capabilities in the first version.

## Current Context

The current backend exposes a single image route, `POST /api/images/generate`, and calls `gpt-image-2` through `backend/app/openai_images.py`. The frontend submits a form from the product workbench and renders one result image.

The agent workflow should be added alongside this route. The existing route can stay as the simple one-shot product image path while the new agent API owns multi-turn editing, conversation state, and image version history.

## Architecture

The high-level flow is:

```txt
Next.js chat workbench
  -> FastAPI agent routes
    -> ImageAgentService
      -> PostgreSQL repositories
      -> ImageStorage
      -> AgentToolRegistry
        -> gpt_image_2_edit
          -> OpenAI Images API using gpt-image-2
```

`ImageAgentService` is the boundary for conversation handling. It loads the session, current image version, and recent messages, calls the agent model, runs allowed tools, persists assistant messages, and advances the current version when an image is produced.

## PostgreSQL Storage

PostgreSQL stores conversation state, tool metadata, and image version relationships. Image binary data should not be stored in PostgreSQL. Store image files in local storage during development and object storage in production, with PostgreSQL keeping `storage_key` and metadata.

Recommended backend dependencies:

- `sqlalchemy`: ORM models and database sessions.
- `psycopg[binary]`: PostgreSQL driver.
- `alembic`: schema migrations.
- `pydantic`: request and response DTOs.

Environment variables:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/image_agent
IMAGE_STORAGE_DIR=backend/storage/images
OPENAI_API_KEY=
OPENAI_AGENT_MODEL=gpt-5.5
OPENAI_IMAGE_MODEL=gpt-image-2
```

## Data Model

`agent_sessions`

- `id uuid primary key`
- `title text`
- `current_version_id uuid nullable`
- `previous_response_id text nullable`
- `status text`
- `created_at timestamptz`
- `updated_at timestamptz`

`agent_messages`

- `id uuid primary key`
- `session_id uuid references agent_sessions(id)`
- `role text`
- `content text`
- `response_id text nullable`
- `tool_call_id text nullable`
- `created_at timestamptz`

`image_versions`

- `id uuid primary key`
- `session_id uuid references agent_sessions(id)`
- `parent_version_id uuid references image_versions(id) nullable`
- `storage_key text`
- `public_url text nullable`
- `mime_type text`
- `width int nullable`
- `height int nullable`
- `prompt text`
- `revised_prompt text nullable`
- `model text`
- `created_at timestamptz`

Restoring a version only updates `agent_sessions.current_version_id`. It does not delete messages or versions.

## API Design

Create a separate agent API namespace:

```txt
POST /api/agent/sessions
POST /api/agent/sessions/{sessionId}/messages
GET /api/agent/sessions/{sessionId}
POST /api/agent/sessions/{sessionId}/versions/{versionId}/restore
```

`POST /api/agent/sessions` creates a session. It accepts the initial image and first user request. The response includes the created session, messages, current image, versions, and any pending clarification question.

`POST /api/agent/sessions/{sessionId}/messages` sends a follow-up instruction. The backend uses the session's `previous_response_id`, current image version, and recent messages as context. It either returns a clarifying assistant message or creates a new image version.

`GET /api/agent/sessions/{sessionId}` returns the persisted session state, messages, versions, and current image.

`POST /api/agent/sessions/{sessionId}/versions/{versionId}/restore` moves the active edit base to an older version.

Use a stable response envelope:

```json
{
  "session": {},
  "messages": [],
  "currentImage": {},
  "versions": [],
  "pendingQuestion": null,
  "error": null
}
```

## Tool System

Define an internal tool interface:

```txt
AgentTool
- name
- description
- input_schema
- permissions
- execute()
```

The first registry contains:

```txt
gpt_image_2_edit
```

The tool receives the current image version, user instruction, product context, and output size. It calls the OpenAI Images API with `OPENAI_IMAGE_MODEL=gpt-image-2`, writes the returned image to `ImageStorage`, and returns an `ImageVersion` candidate for persistence.

Future adapters can implement the same interface:

- `McpToolAdapter`
- `SkillToolAdapter`
- `ImageAnalysisTool`
- `BrandGuidelineTool`
- `ProductCatalogTool`

The agent may choose from registered tools, but it must not install tools, load arbitrary skills, or execute unapproved local code.

## MCP And Skill Boundaries

MCP and skill support should be whitelist based. Each external capability needs a configured id, exposed tools, timeout, and approval policy.

Example MCP config shape:

```txt
mcp_servers:
- id
- name
- command_or_url
- enabled_tools
- timeout_ms
- requires_approval
```

Example skill config shape:

```txt
skills:
- id
- name
- entrypoint
- input_schema
- output_schema
- sandbox_policy
```

This keeps the agent extensible without allowing user prompts to become arbitrary code execution.

## Frontend Experience

Replace the one-shot form flow with a conversation workbench for the agent route:

- Current image canvas in the main visual area.
- Chat thread for user instructions and assistant clarifications.
- Version strip showing image history.
- Restore action for each previous version.
- Upload state for the initial image.
- Disabled submit state while an agent request is running.
- Error and retry controls near the message that failed.

The existing product fields can become session context for the first message, rather than mandatory controls on every turn.

## Error Handling

Use four explicit error categories:

- `UserInputError`: invalid file, missing initial image, empty instruction, unsupported size. Return 400.
- `AgentClarification`: the agent needs more information. Return a normal 200 response with `pendingQuestion`.
- `ToolExecutionError`: OpenAI call, timeout, or generation failure. Return 502 and keep the user message for retry.
- `StorageError`: database or image storage failure. Return 500 with a generic user-facing message and detailed server logs.

Tool failures should not corrupt the active session state. If image storage succeeds but database persistence fails, the service should log the orphaned `storage_key` for cleanup.

## Testing

Backend tests:

- Creating a session persists `agent_sessions`, the first `agent_messages` row, and the initial `image_versions` row.
- Sending a clear follow-up instruction calls `gpt_image_2_edit` and creates a child image version.
- Sending an ambiguous instruction can return `pendingQuestion` without creating an image version.
- Restoring a version updates only `current_version_id`.
- OpenAI calls are mocked or faked; unit tests must not call the live API.
- Repository tests cover PostgreSQL persistence separately from service tests.

Frontend tests:

- The chat composer sends messages and shows pending state.
- The current image updates when a new version is returned.
- The version strip renders parent and child versions.
- Restore calls the restore route and updates the active image.
- Clarifying questions render as assistant messages without adding image versions.
- Tool errors are shown with retry affordance.

## Rollout

Implement this in phases:

1. Add PostgreSQL configuration, SQLAlchemy models, Alembic migrations, and repository tests.
2. Add image storage and version persistence.
3. Add the agent service with a fake tool for deterministic tests.
4. Wire `gpt_image_2_edit` to the OpenAI Images API with `gpt-image-2`.
5. Add FastAPI agent routes.
6. Add the Next.js conversation workbench.
7. Add MCP and skill adapters only after the core agent loop is stable.

## References

- OpenAI image generation guide: https://developers.openai.com/api/docs/guides/image-generation
- OpenAI image generation tool guide: https://developers.openai.com/api/docs/guides/tools-image-generation
- OpenAI conversation state guide: https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI `gpt-image-2` model reference: https://developers.openai.com/api/docs/models/gpt-image-2
