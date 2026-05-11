# ChatGPT Conversation Request Failure Findings

## Initial Code Map
- Frontend sends current conversation requests through `frontend/src/lib/agent-api.ts`, `sendConversationMessage()`, to `POST /api/agent/conversation`.
- Backend route is `backend/app/main.py::send_conversation_message`.
- Route requires `get_current_user`, reads multipart form uploads, and calls `run_agent_service("send_message", ...)` in a threadpool.
- In-memory service path is `backend/app/agent_service.py::ChatGptConversationService._send_in_memory_message`.
- Planner call goes to `backend/app/agent_openai.py::request_conversation_turn`.
- Existing tests cover route behavior in `backend/tests/test_agent_routes.py` and OpenAI planner behavior in `backend/tests/test_agent_openai.py`.

## Open Questions
- Whether failure reproduces as unauthenticated request, backend 500, OpenAI client parameter error, malformed model output, or frontend error handling.

## Reproduction
- Existing local services are running on `127.0.0.1:8000` and `127.0.0.1:3000`.
- `GET /health` returns `{"ok": true}`.
- Unauthenticated `GET /api/agent/sessions` returns `401 {"error":"请先登录。"}`.
- After registering a temporary user and posting a text-only form to `POST /api/agent/sessions`, the API returns `500 {"error":"Agent request failed."}`.

## Root Cause Evidence
- Directly calling `build_agent_service(db).create_session(...)` in the same runtime shows:
  - `OPENAI_API_KEY_SET=False`
  - `OPENAI_AGENT_MODEL=gpt-5.4-mini`
  - OpenAI SDK raises `openai.OpenAIError: Missing credentials. Please pass an api_key...`
- The backend catches generic exceptions in agent routes and maps this to `Agent request failed.`, hiding the actionable configuration error from the UI.
- After `OPENAI_API_KEY` and `OPENAI_BASE_URL` were set in `backend/.env.example`, a fresh Python process loaded them correctly, but the running HTTP server still saw the key as empty until reload.
- Cause: `python-dotenv` with `override=False` does not override an existing empty process env var. Clearing empty OpenAI-related env vars before loading env files lets `.env.example` act as the fallback it is intended to be.
