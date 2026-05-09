# Dark Creative Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the frontend as a dark, image-first AI creation studio.

**Architecture:** Keep the current Next.js App Router structure and existing API submission flow. Change only visual shell, layout, source-level regression tests, and presentational data used for inspiration thumbnails.

**Tech Stack:** Next.js, React, Tailwind CSS v4, lucide-react, node:test.

---

### Task 1: Visual Regression Tests

**Files:**
- Modify: `frontend/tests/homepage-layout.test.mjs`
- Modify: `frontend/tests/visual-refinement.test.mjs`

- [ ] Replace white-toolbox assertions with checks for a left rail, inspiration gallery, prompt composer, dark studio tokens, sample visual tiles, and dark workbench shells.
- [ ] Run `rtk npm test` from `frontend`.
- [ ] Expected red result: tests fail because the current source still uses the white layout.

### Task 2: Global Dark Theme

**Files:**
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/app/layout.tsx`

- [ ] Set `paper` to dark charcoal and add `surface`, `surface-soft`, `line`, `cyan`, `coral`, and `gold` theme colors.
- [ ] Add subtle grid/noise body background and dark scrollbar styling.
- [ ] Use `Noto_Sans_SC`, `Noto_Serif_SC`, and `IBM_Plex_Mono` font variables.
- [ ] Run `rtk npm test`; expected: theme-related tests pass once page files are updated.

### Task 3: Homepage Studio

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/tool-card.tsx`

- [ ] Build the homepage as a three-zone studio: left rail, central visual gallery, right settings panel, bottom prompt composer.
- [ ] Use real remote image thumbnails in cards through standard `<img>` tags with dark overlays.
- [ ] Keep tool navigation generated from `imageTools`.
- [ ] Run `rtk npm test`; expected: homepage tests pass.

### Task 4: Tool Workbenches

**Files:**
- Modify: `frontend/src/app/tools/[toolId]/page.tsx`
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/src/components/tool-form.tsx`

- [ ] Redesign the route shell with a dark header, compact breadcrumb, tool identity, and creator status chips.
- [ ] Redesign `ProductWorkbench` into left source panel, middle strategy panel, right canvas, and bottom constraints/composer section.
- [ ] Redesign `ToolForm` into a dark prompt controls panel plus large visual canvas with non-empty sample preview.
- [ ] Keep all form state, submission fields, and error handling behavior.
- [ ] Run `rtk npm test`; expected: all source-level tests pass.

### Task 5: Verification

**Files:**
- All modified frontend files.

- [ ] Run `rtk npm test`.
- [ ] Run `rtk npm run lint`.
- [ ] Run `rtk npm run build`.
- [ ] Run `rtk proxy git diff --check`.
- [ ] Capture desktop/mobile screenshots from the running dev server and inspect for blank panels, white dominant surfaces, clipped text, or broken layout.
