# Streaming Agent And Parallel Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stream ChatGPT conversation responses to the UI and generate multi-image requests concurrently without changing default high image quality.

**Architecture:** Add SSE endpoints that expose typed events from the persisted `ChatGptConversationService` turn flow. Keep the existing JSON endpoints as fallback/source-compatible behavior. Parallelize repeated OpenAI image calls in `openai_images.py` with ordered results.

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI Python SDK Responses API, React/Next.js, browser `fetch` streaming.

---

### Task 1: Parallel Multi-Image Generation

**Files:**
- Modify: `backend/app/openai_images.py`
- Test: `backend/tests/test_openai_images.py`

- [ ] Add a failing test that starts four image requests behind a blocking gate and asserts all requests have started before any response is released.
- [ ] Run `rtk pytest backend/tests/test_openai_images.py::test_requests_multiple_images_concurrently -q` and confirm it fails because calls are serial.
- [ ] Use `ThreadPoolExecutor` in `request_image_from_openai` when `image_count > 1`, preserving result order.
- [ ] Run `rtk pytest backend/tests/test_openai_images.py -q` and confirm it passes.

### Task 2: Streaming Planner And Service Events

**Files:**
- Modify: `backend/app/agent_openai.py`
- Modify: `backend/app/agent_service.py`
- Test: `backend/tests/test_agent_openai.py`
- Test: `backend/tests/test_agent_service.py`

- [ ] Add a failing planner test proving response text deltas are emitted and the final JSON decision still parses.
- [ ] Add a failing service test proving streamed create-session events include `session`, `user_message`, `assistant_delta`, and `final`.
- [ ] Run the two focused tests and confirm they fail for missing streaming APIs.
- [ ] Implement `request_conversation_turn_stream` and service event generation.
- [ ] Run `rtk pytest backend/tests/test_agent_openai.py backend/tests/test_agent_service.py -q`.

### Task 3: SSE Routes

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_agent_routes.py`

- [ ] Add a failing route test for `/api/agent/sessions/stream` that asserts `text/event-stream` and parsed event payloads.
- [ ] Run the focused route test and confirm it fails.
- [ ] Implement `StreamingResponse` SSE helpers and stream routes.
- [ ] Run `rtk pytest backend/tests/test_agent_routes.py -q`.

### Task 4: Frontend Streaming Client And Workbench

**Files:**
- Modify: `frontend/src/lib/agent-api.ts`
- Modify: `frontend/src/components/agent-image-workbench.tsx`
- Test: `frontend/tests/agent-workbench.test.mjs`

- [ ] Add failing frontend tests for `streamAgentSession`, `streamAgentSessionMessage`, and incremental assistant state markers in the workbench.
- [ ] Run `rtk npm test -- agent-workbench.test.mjs` from `frontend` and confirm failure.
- [ ] Implement SSE parsing helpers and update `handleSubmit` to consume streaming events.
- [ ] Run `rtk npm test -- agent-workbench.test.mjs` and `rtk npm run lint`.

### Task 5: Final Verification

**Files:**
- All touched files

- [ ] Run backend focused tests: `rtk pytest backend/tests/test_openai_images.py backend/tests/test_agent_openai.py backend/tests/test_agent_service.py backend/tests/test_agent_routes.py -q`.
- [ ] Run frontend tests: `rtk npm test -- agent-workbench.test.mjs` from `frontend`.
- [ ] Run `rtk git diff --stat` and review the final diff.
