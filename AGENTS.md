<INSTRUCTIONS>
@C:\Users\Administrator\.codex\RTK.md

# Project Workflow

This project prefers a fast, focused development path. Keep the safety checks that
matter, but avoid heavy planning rituals for small, low-risk changes.

## Fast Path

Use the fast path for:

- Small bug fixes with a clear root cause.
- Minor UI, copy, style, or configuration updates.
- Test-only changes.
- Mechanical refactors that do not alter behavior.

Fast path rules:

- Do not create design docs or implementation plans unless the user asks for one.
- Do not use full brainstorming for simple, already-approved work.
- Run the smallest relevant focused test first.
- Before claiming completion, run fresh verification that matches the change.

## Full Workflow

Use the heavier planning workflow for:

- New product behavior or major features.
- Multi-file changes with unclear architecture.
- Risky data, payment, auth, storage, or API contract changes.
- Broad frontend redesigns.
- Any task where the user explicitly asks for a plan, design, TDD, review, or PR.

## Code Search

Avoid broad recursive scans over generated or dependency folders. Prefer `rg` with
exclusions:

```powershell
rtk rg --files -g '!frontend/node_modules/**' -g '!frontend/.next/**' -g '!backend/.venv/**' -g '!backend/.pytest_cache/**' -g '!test-results/**'
```

Do not use unbounded `Get-ChildItem -Recurse` from the repository root.

## Verification

Use focused verification while iterating, then choose the smallest final command
that proves the touched behavior:

- Backend: `rtk pytest backend/tests/<focused-test>.py -q`
- Frontend: run from `frontend`, e.g. `rtk npm test -- <focused-test>.mjs`
- Lint/build only when the touched files or task risk warrants it.
</INSTRUCTIONS>
