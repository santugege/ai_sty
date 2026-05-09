# Product Prompt Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require an uploaded original image for product image generation and replace the Agent conversation panel with a read-only final prompt preview.

**Architecture:** The frontend product workbench builds and displays the submitted prompt from selected ecommerce settings and the user's requirement. The backend product tool is the source of truth for upload requirement validation by setting `image_required=True`.

**Tech Stack:** Next.js/React/TypeScript frontend, FastAPI/Python backend, Node test runner, pytest.

---

### Task 1: Backend Upload Requirement

**Files:**
- Modify: `backend/app/tools.py`
- Modify: `backend/tests/test_tools.py`
- Modify: `backend/tests/test_image_request.py`

- [ ] **Step 1: Write failing backend tests**

Update product tool/request tests so the product tool requires an image and missing uploads fail.

- [ ] **Step 2: Run backend tests to verify red**

Run: `python -m pytest backend/tests/test_tools.py backend/tests/test_image_request.py`
Expected: FAIL because `tool.image_required` is currently false and a product request without upload is allowed.

- [ ] **Step 3: Implement minimal backend change**

Set `image_required=True` for the product `ImageTool` and update the base prompt so it no longer describes no-image direction drafts.

- [ ] **Step 4: Run backend tests to verify green**

Run: `python -m pytest backend/tests/test_tools.py backend/tests/test_image_request.py`
Expected: PASS.

### Task 2: Frontend Prompt Preview

**Files:**
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/tests/homepage-layout.test.mjs`
- Modify: `frontend/tests/visual-refinement.test.mjs`

- [ ] **Step 1: Write failing frontend tests**

Update source-level tests to require `userRequirement`, `finalPromptPreview`, required upload copy, read-only prompt preview markup, and absence of `chatMessages`/Agent conversation labels.

- [ ] **Step 2: Run frontend tests to verify red**

Run: `npm test -- homepage-layout.test.mjs visual-refinement.test.mjs`
Expected: FAIL because the current workbench still contains chat/Agent state and optional upload messaging.

- [ ] **Step 3: Implement minimal frontend change**

Rename chat state to user requirement state, remove chat message state/rendering, validate that `file` exists before submission, build `finalPromptPreview`, submit it as `prompt`, and render the right panel as a read-only prompt preview plus requirement textarea.

- [ ] **Step 4: Run frontend tests to verify green**

Run: `npm test -- homepage-layout.test.mjs visual-refinement.test.mjs`
Expected: PASS.

### Task 3: Full Verification

**Files:**
- Verify only.

- [ ] **Step 1: Run all frontend tests**

Run: `npm test`
Expected: PASS.

- [ ] **Step 2: Run all backend tests from repo root**

Run: `python -m pytest backend`
Expected: PASS.

- [ ] **Step 3: Run frontend lint/build if tests pass**

Run: `npm run lint` and `npm run build`
Expected: PASS.
