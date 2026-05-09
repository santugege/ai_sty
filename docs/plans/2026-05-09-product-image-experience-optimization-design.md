# Product Image Experience Optimization Design

Date: 2026-05-09

## Goal

Turn the current product image generator into a task-oriented ecommerce image workbench. The user should feel they are producing a usable listing asset, not tuning a generic image model.

## Current Context

The project already has two relevant flows:

- `frontend/src/components/product-workbench.tsx` submits one-shot product generation requests to `POST /api/images/generate`.
- `frontend/src/components/agent-image-workbench.tsx` uses `/api/agent` routes for multi-turn editing, image versions, and restore.

The backend also already has the important foundations:

- `backend/app/image_request.py` validates product fields and composes product prompts.
- `backend/app/openai_images.py` can generate multiple images through `image_count`.
- `backend/app/agent_service.py` persists an editable image session with message and version history.

The current experience exposes these capabilities as separate surfaces. Users can generate a product image, or go to a separate multi-turn edit page, but the product workflow does not yet feel continuous.

## Product Diagnosis

The user wants a commercially usable product image. The current interface asks them to choose parameters before it has helped them define the product task.

Key issues:

- The workflow is parameter-first instead of outcome-first.
- Product context is too thin: category, selling points, preservation rules, and negative constraints are not first-class in the current compact workbench.
- The frontend only uses the first generated image even though the backend can return multiple candidates.
- Generation has weak progress feedback for a slow AI task.
- The multi-turn agent and version history live in a separate route, so iteration feels like a different feature rather than the natural next step.
- Post-generation actions are underdeveloped: no candidate comparison, quick edits, download, or restore path in the main product surface.

## Product Direction

Use a unified "generation task workbench" model.

The first screen should guide the user through a clear production path:

1. Upload or start from a direction draft.
2. Complete a concise product brief.
3. Choose platform, image purpose, aspect ratio, and output size.
4. Generate two to four candidates.
5. Select the best candidate.
6. Continue editing the selected candidate through short instructions.
7. Compare versions, restore, download, or generate another batch.

This keeps the app focused on the ecommerce operator's job: quickly producing a usable product image and refining it without losing work.

## Recommended Architecture

Keep both backend namespaces, but make the frontend present them as one workflow:

- `/api/images/generate`: first-pass candidate generation.
- `/api/agent/sessions`: creates an editable session from a selected image candidate.
- `/api/agent/sessions/{sessionId}/messages`: follow-up edits.
- `/api/agent/sessions/{sessionId}/versions/{versionId}/restore`: version restore.

The main workbench becomes the product home. The standalone `/agent` route can remain as a legacy or advanced editing entry, but the primary path should not require users to navigate there.

## Experience Design

### Input Brief

Replace the left-side parameter list with a compact brief builder:

- Upload area with file status and preview.
- Product prompt textarea.
- Selling points textarea.
- Preserve requirements textarea.
- Avoid elements textarea.
- Optional chips for common examples.

The product brief should be visible near the generation button so users understand what will drive the result.

### Strategy Panel

Keep platform, purpose, aspect ratio, size, and image count, but present them as grouped controls:

- Platform preset: Pinduoduo, Taobao/Tmall, JD, Xiaohongshu, Douyin.
- Image purpose: main image, white background, scene image, promotion image, detail hero.
- Canvas: aspect ratio and output size.
- Batch: one, two, or four candidates.

The UI should show a one-line summary such as: `淘宝/天猫 · 主图 · 1:1 · 2 张`.

### Generation State

Generation should show clear task progress:

- Validating product brief.
- Preparing prompt.
- Generating candidate images.
- Rendering results.

The backend does not need true streaming for the first version. The frontend can show deterministic staged status while the request is pending, then replace it with the real result.

### Candidate Results

Render every image returned by the backend:

- Large selected preview in the canvas.
- Candidate thumbnails with labels like `方案 A`, `方案 B`.
- Revised prompt shown for the selected candidate.
- Actions: select, continue editing, download.

The user should not lose candidates when they start editing one of them.

### Editing Loop

Once a candidate is selected, the user can start an agent session from it and continue with short instructions:

- Make the background cleaner.
- Enlarge the product.
- Keep package text readable.
- Reserve space on the right for promotion text.

The version strip should sit close to the canvas. Restore should feel like undoing to a previous usable image.

### Error Handling

Errors should appear in context:

- Invalid image: near upload.
- Missing brief: near prompt.
- Safety or model failure: in the action/status bar with retry.
- Agent edit failure: attached to the failed instruction.

All errors should preserve user input and generated candidates.

## Scope

The first implementation should focus on the main product workflow:

- Fix visible Chinese copy and encoding-sensitive text in the touched files.
- Return and render all generated images.
- Add product brief fields back to the product workbench.
- Add generation status feedback.
- Add candidate selection, download, and quick edit entry points.
- Bridge selected candidates into the existing agent session flow.

Do not add account systems, payment, asset library persistence, brand kits, or platform publishing in this phase.

## Success Criteria

- A new user can understand what to do from the first screen without reading instructions.
- The user can generate multiple candidates and choose one.
- The user can continue editing a chosen candidate without switching mental contexts.
- The user can restore previous versions during editing.
- The UI preserves inputs and candidates after errors.
- The product surface uses readable Chinese copy throughout.
- Existing backend tests still pass, and frontend tests cover the new candidate and edit handoff states.
