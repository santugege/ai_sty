# Agent Image Tool Chain Audit Findings

Date: 2026-05-11

## Findings

- Frontend active workbench now calls only persisted session APIs: `listAgentSessions`, `createAgentSession`, `getAgentSession`, and `sendAgentSessionMessage`.
- Frontend no longer imports or renders a dedicated current image context panel. Selected images only exist as composer draft attachments and are cleared immediately after submit.
- The send button no longer shows a submit spinner. The waiting state is represented in the message stream with `ReceivingBubble`, so the UI reads as "receiving reply" rather than "message still sending."
- Frontend API client no longer exports old single-conversation helpers: `sendConversationMessage` and `resetConversation`.
- Backend no longer exposes old in-memory routes: `POST /api/agent/conversation` and `POST /api/agent/conversation/reset`.
- Backend `main.py` no longer has a global `conversation_service`, `build_conversation_service()`, or `run_agent_service()`.
- `ChatGptConversationService` no longer has an in-memory `repo is None` branch, `send_message()`, `reset()`, `ConversationState`, or top-level `currentImage` envelope construction.
- `AgentEnvelope` no longer exposes `currentImage`; generated images live on assistant messages, and uploaded images live on user message attachments.
- Backend still keeps `current_version_id` internally. This is not UI state; it is the persisted session pointer used at tool execution time to decide which image bytes to pass to `gpt_image_2_edit`.
- Removed the old `request_agent_decision(current_image_summary=...)` compatibility wrapper so the active planner path is `request_conversation_turn(...)`.
- Residual source search found old names only inside negative tests that prevent the legacy behavior from returning.
