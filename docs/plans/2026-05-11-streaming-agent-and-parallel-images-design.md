# Streaming Agent And Parallel Images Design

## Goal

Make the ChatGPT conversation feel live by streaming assistant progress to the UI, and reduce multi-image wait time by generating requested image variants concurrently while keeping the default OpenAI image quality at `high`.

## Architecture

The backend keeps the existing persisted conversation flow as the source of truth. A new service method emits typed events during a turn: session creation, persisted user message, assistant text/progress, image generation progress, final envelope, and errors. FastAPI exposes those events as Server-Sent Events for create-session and send-message requests. The frontend consumes the stream with `fetch` and a `ReadableStream`, updates local state immediately, and reconciles with the final persisted envelope.

Image generation keeps the same prompt composition, model, and `quality="high"`. When `image_count` is greater than one, `request_image_from_openai` dispatches one request per image through a small thread pool and returns results in request order.

## Components

- `backend/app/agent_openai.py`: add an optional streaming planner path that accumulates Responses API text deltas and emits them before parsing the final decision JSON.
- `backend/app/agent_service.py`: add turn event dataclasses and streaming create/send methods that reuse the existing persistence, rollback, and tool execution logic.
- `backend/app/main.py`: add SSE responses for streamed agent create/send routes.
- `backend/app/openai_images.py`: parallelize repeated image calls while preserving ordered results and high quality.
- `frontend/src/lib/agent-api.ts`: add an SSE parser and streaming helpers.
- `frontend/src/components/agent-image-workbench.tsx`: call streaming helpers and render the assistant bubble incrementally.

## Testing

Add backend tests for ordered concurrent multi-image generation, streaming planner deltas, service event order, and SSE route shape. Add frontend source/API tests that confirm streaming routes, stream parsing, and workbench state updates are wired.
