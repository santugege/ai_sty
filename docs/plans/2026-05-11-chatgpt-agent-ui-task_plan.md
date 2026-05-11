# ChatGPT Agent UI Task Plan

Date: 2026-05-11

## Goal

- Keep the ChatGPT conversation experience in the same page flow, matching the product image workbench logic instead of navigating to an isolated page.
- Redesign all pages so their UI follows the `/agent` page direction.

## Phases

- [x] Capture task scope and project rules.
- [x] Explore current routes, shared layout, `/agent`, product image flow, and tests.
- [x] Present a concise design and get approval.
- [x] Write failing tests for the approved behavior and visual contracts.
- [x] Implement the changes.
- [x] Run focused and broad verification.

## Decisions

- Respect `AGENTS.md` instruction to prefix shell commands with `rtk`.
- Use `/agent` as the visual source of truth unless exploration shows a shared design layer already exists.

## Verification

- `rtk npm test --prefix frontend` passed: 41/41 tests.
- `rtk npm run lint --prefix frontend` passed.
- `rtk npm run build --prefix frontend` passed.
- `curl.exe -I http://localhost:3000/agent` returned HTTP 200 from the existing local Next dev server.
