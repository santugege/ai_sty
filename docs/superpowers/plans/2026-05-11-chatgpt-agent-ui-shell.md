# ChatGPT Agent UI Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put ChatGPT conversation into the same app workbench shell as product image generation and align main pages with that shell.

**Architecture:** Add a shared `AppShell` component that owns the `AppNav` rail and content dock. Update product, ChatGPT, billing, payment return, and admin pages to use it; keep auth pages standalone but visually aligned. Add source-level tests before implementation.

**Tech Stack:** Next.js App Router, React, Tailwind CSS, Node test runner.

---

### Task 1: Shell Contract Tests

**Files:**
- Modify: `frontend/tests/homepage-layout.test.mjs`
- Modify: `frontend/tests/agent-workbench.test.mjs`

- [ ] Add tests that require `AppShell`, `homepageShell`, and `homepageWorkbenchDock` to live in a shared component.
- [ ] Add tests that require `/agent` to use `AppShell` and render `AgentImageWorkbench` with `variant="compact"`.
- [ ] Run `rtk npm test --prefix frontend -- homepage-layout.test.mjs agent-workbench.test.mjs` and verify failure before production code changes.

### Task 2: Shared App Shell

**Files:**
- Create: `frontend/src/components/app-shell.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/agent/page.tsx`

- [ ] Create `AppShell` with `AppNav`, `homepageShell`, and `homepageWorkbenchDock`.
- [ ] Move homepage onto `AppShell`.
- [ ] Move `/agent` onto `AppShell` and pass compact variant to `AgentImageWorkbench`.
- [ ] Run focused shell tests and verify they pass.

### Task 3: Embedded ChatGPT Workbench

**Files:**
- Modify: `frontend/src/components/agent-image-workbench.tsx`

- [ ] Add `variant?: "full" | "compact"` and compact height behavior.
- [ ] Replace hardcoded colors with shared design tokens.
- [ ] Preserve session list, draft clearing, composer, upload previews, and current image context.
- [ ] Run agent tests.

### Task 4: Main Page Alignment

**Files:**
- Modify: `frontend/src/app/billing/page.tsx`
- Modify: `frontend/src/app/payments/return/page.tsx`
- Modify: `frontend/src/app/admin/subscriptions/page.tsx`
- Modify: `frontend/src/app/admin/accounts/page.tsx`
- Modify: `frontend/src/app/tools/[toolId]/page.tsx`

- [ ] Use `AppShell` for authenticated pages.
- [ ] Remove the old `Studio Matrix` top bar from the product tool route.
- [ ] Preserve all page behavior and form submissions.
- [ ] Run existing page tests.

### Task 5: Verification

**Files:**
- All modified frontend files.

- [ ] Run `rtk npm test --prefix frontend`.
- [ ] Run `rtk npm run lint --prefix frontend`.
- [ ] Run `rtk npm run build --prefix frontend` if lint and tests pass.
