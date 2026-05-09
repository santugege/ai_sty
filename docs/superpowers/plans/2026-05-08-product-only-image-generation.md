# Product-Only Image Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every non-product image feature while preserving ecommerce product image generation.

**Architecture:** Keep the existing `/api/images/generate` API and product workbench flow. Narrow frontend and backend tool registries to `product`, remove generic tool UI entry points, and update tests so removed tool ids are rejected.

**Tech Stack:** FastAPI, pytest, Next.js, React, TypeScript, Node test runner.

---

## File Structure

- Modify `backend/app/tools.py`: product-only tool registry.
- Modify `backend/app/image_request.py`: remove non-product prompt path and keep product validation.
- Modify `backend/tests/test_tools.py`: assert product-only registry.
- Modify `backend/tests/test_image_request.py`: assert removed ids fail and product flow remains valid.
- Modify `backend/tests/test_main.py`: remove restore route expectations and keep product route expectations.
- Modify `frontend/src/lib/tools.ts`: product-only frontend registry and product option types.
- Modify `frontend/src/app/tools/[toolId]/page.tsx`: only `/tools/product` renders.
- Delete `frontend/src/components/tool-card.tsx`: unused after product-only homepage.
- Delete `frontend/src/components/tool-form.tsx`: unused generic tool form.

---

### Task 1: Backend Registry Tests

**Files:**
- Modify: `backend/tests/test_tools.py`
- Modify: `backend/app/tools.py`

- [ ] **Step 1: Write failing product-only registry tests**

Replace tests that expect four tools with:

```python
def test_defines_only_product_tool():
    assert [tool.id for tool in image_tools] == ["product"]


def test_removed_tools_are_not_available():
    assert get_tool_by_id("creator") is None
    assert get_tool_by_id("restore") is None
    assert get_tool_by_id("avatar") is None


def test_product_tool_is_edit_capable():
    assert get_tool_by_id("product").mode == "edit"
```

- [ ] **Step 2: Verify tests fail before implementation**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_tools.py -q`

Expected: FAIL because the registry still contains creator, restore, and avatar.

- [ ] **Step 3: Narrow backend registry**

In `backend/app/tools.py`, change `ToolId` to only `"product"` and remove `creator`, `restore`, and `avatar` entries from `image_tools`.

- [ ] **Step 4: Verify registry tests pass**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_tools.py -q`

Expected: PASS.

### Task 2: Backend Request Validation Tests

**Files:**
- Modify: `backend/tests/test_image_request.py`
- Modify: `backend/app/image_request.py`

- [ ] **Step 1: Write failing validation tests for removed ids**

Add or update tests so `validate_image_form("restore", ...)`, `validate_image_form("creator", ...)`, and `validate_image_form("avatar", ...)` each raise `ImageRequestError` with status `400`.

- [ ] **Step 2: Verify tests fail before implementation**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_request.py -q`

Expected: FAIL if any tests still expect non-product behavior.

- [ ] **Step 3: Remove non-product prompt branch**

In `compose_tool_prompt`, keep the product prompt path and return the product prompt. Remove the generic fallback branch for non-product tools.

- [ ] **Step 4: Verify image request tests pass**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_request.py -q`

Expected: PASS.

### Task 3: Backend Route Tests

**Files:**
- Modify: `backend/tests/test_main.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Replace non-product route test expectations**

Remove tests that post `toolId=restore`, `toolId=creator`, or `toolId=avatar`. Keep tests for product requests with uploaded image and structured product fields.

- [ ] **Step 2: Verify route tests fail before implementation if route still accepts removed ids**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_main.py -q`

Expected: FAIL if route tests still assume removed tools are valid.

- [ ] **Step 3: Keep route API stable**

Leave `backend/app/main.py` route and form field names intact. The product-only behavior comes from `validate_image_form` and the narrowed registry.

- [ ] **Step 4: Verify route tests pass**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests/test_main.py -q`

Expected: PASS.

### Task 4: Frontend Product-Only Registry and Routes

**Files:**
- Modify: `frontend/src/lib/tools.ts`
- Modify: `frontend/src/app/tools/[toolId]/page.tsx`
- Delete: `frontend/src/components/tool-card.tsx`
- Delete: `frontend/src/components/tool-form.tsx`

- [ ] **Step 1: Write or update frontend test expectations**

Update Node tests so they assert only product-related page content and no creator, restore, or avatar labels/routes are expected.

- [ ] **Step 2: Run frontend tests before implementation**

Run: `rtk npm test --prefix frontend`

Expected: FAIL if tests still expect removed generic tools.

- [ ] **Step 3: Narrow frontend registry**

Set `ToolId = "product"`, remove unused non-product icon/accent options if no remaining component uses them, and keep only the product object in `imageTools`.

- [ ] **Step 4: Restrict dynamic tool route**

Render `ProductWorkbench` only when `params.toolId === "product"` and call `notFound()` for all other ids.

- [ ] **Step 5: Delete unused generic components**

Delete `frontend/src/components/tool-card.tsx` and `frontend/src/components/tool-form.tsx` after confirming no imports remain.

- [ ] **Step 6: Verify frontend**

Run:

```bash
rtk npm test --prefix frontend
rtk npm run lint --prefix frontend
rtk npm run build --prefix frontend
```

Expected: all commands exit with code 0.

### Task 5: Full Verification

**Files:**
- No new edits unless verification reveals a defect.

- [ ] **Step 1: Run backend suite**

Run: `rtk backend/.venv/Scripts/python -m pytest backend/tests -q`

Expected: PASS.

- [ ] **Step 2: Run frontend suite**

Run:

```bash
rtk npm test --prefix frontend
rtk npm run lint --prefix frontend
rtk npm run build --prefix frontend
```

Expected: PASS.
