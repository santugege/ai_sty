# Figma UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new Figma desktop screen for the product image generation app as a professional ecommerce image command center.

**Architecture:** Create a new Figma design file, define a local token-like visual system directly in the file, then compose one complete desktop screen with reusable component frames. Validate with screenshots after the major build steps and refine spacing, text, and hierarchy before delivery.

**Tech Stack:** Figma MCP `create_new_file`, `use_figma`, Figma Plugin API, local project context from the Next.js frontend.

---

### Task 1: Create Figma File And Page Foundation

**Files:**
- Read: `frontend/src/components/home-product-workbench.tsx`
- Read: `frontend/src/app/globals.css`
- Create in Figma: `Ecommerce Product Image Workbench UI Redesign`

- [ ] **Step 1: Create a new Figma design file**

Use the authenticated team plan key and create a design file named `Ecommerce Product Image Workbench UI Redesign`.

- [ ] **Step 2: Inspect the empty file**

Run a read-only `use_figma` script to list pages and confirm the file is editable.

- [ ] **Step 3: Create a `Command Center` page**

Create or rename the first page to `Command Center`, set up a 1440px desktop frame named `Professional Ecommerce Image Command Center`, and return the frame ID.

### Task 2: Build The Visual System

**Files:**
- Read: `docs/plans/2026-05-09-figma-ui-redesign-design.md`
- Create in Figma: colors, text styles, and component-like local frames

- [ ] **Step 1: Load required fonts**

Load `Inter Regular`, `Inter Medium`, `Inter Semi Bold`, and `Inter Bold` if available. Fall back to `Arial` only if the font load fails.

- [ ] **Step 2: Create local styles and helper functions**

Use reusable JavaScript helpers for colors, text nodes, auto-layout frames, and button/control construction.

- [ ] **Step 3: Establish the palette**

Use warm light gray background, white panels, graphite text, coral action, teal active state, amber warning, and cool gray borders.

### Task 3: Compose The Desktop Screen

**Files:**
- Read: `frontend/src/components/home-product-workbench.tsx`
- Create in Figma: full desktop app frame

- [ ] **Step 1: Add the left navigation rail**

Include brand, navigation items, compact status, and settings entry.

- [ ] **Step 2: Add the main canvas**

Build a large output preview area with empty-state image guides, a result-state preview card, canvas controls, and revised prompt log.

- [ ] **Step 3: Add the prompt and upload panel**

Include upload drop zone, prompt input, product selling points, preservation requirements, and reference image chips.

- [ ] **Step 4: Add the strategy inspector**

Include platform presets, image purpose, aspect ratio segmented control, scene, tone, and negative constraint fields.

- [ ] **Step 5: Add the bottom action bar**

Include selected configuration summary, error/status area, and a primary `Generate product image` button.

### Task 4: Validate And Refine

**Files:**
- Update in Figma: `Professional Ecommerce Image Command Center`

- [ ] **Step 1: Capture a screenshot of the full frame**

Use `get_screenshot` at a high enough dimension to inspect text and panel spacing.

- [ ] **Step 2: Fix visible problems**

Adjust any clipped text, overly rounded controls, awkward spacing, weak contrast, or overlapping elements.

- [ ] **Step 3: Capture final screenshot**

Confirm the final Figma screen is complete and share the file URL.
