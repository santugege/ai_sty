# Image Toolbox Website Design

Date: 2026-05-07

## Goal

Build a real image generation toolbox website powered by OpenAI image models. The first version lets users choose an image tool, submit text and optional image uploads, and receive generated or edited images without exposing the OpenAI API key in the browser.

## Product Shape

The first screen is a toolbox, not a marketing landing page. Users choose one of four tools:

- AI Image Creator: generate an image from a text prompt.
- Old Photo Restoration: upload an old photo and request restoration such as scratch removal, color recovery, and blur improvement.
- Avatar and Portrait Generator: upload a reference image or describe a visual style to create an avatar or portrait.
- Product Image Generator: upload a product image and request a new background, scene, or ecommerce presentation.

Each tool has its own page, but the pages are driven by shared configuration so new tools can be added with low duplication.

## Architecture

Use a separated frontend and Python backend:

- `frontend/`: Next.js App Router, TypeScript, and Tailwind CSS.
- `backend/`: FastAPI, OpenAI Python SDK, pytest, and environment-based configuration.
- Frontend responsibilities: toolbox home page, tool detail pages, dynamic forms, upload controls, generation status, error messages, and image results.
- Backend responsibilities: request validation, file validation, prompt composition, OpenAI Images API calls, and stable JSON responses.
- Secrets: `OPENAI_API_KEY` is stored only in the Python backend environment, such as `backend/.env` during local development.

The frontend never receives or stores the OpenAI API key.

## Project Structure

The implementation should use this layout:

- `frontend/src/app/page.tsx`: toolbox homepage.
- `frontend/src/app/tools/[toolId]/page.tsx`: dynamic tool page.
- `frontend/src/components/tool-card.tsx`: homepage tool card.
- `frontend/src/components/tool-form.tsx`: client form, upload, submit state, errors, and result display.
- `frontend/src/lib/tools.ts`: frontend display registry for the four tools.
- `backend/app/main.py`: FastAPI app and `POST /api/images/generate`.
- `backend/app/tools.py`: backend tool registry with ids matching the frontend.
- `backend/app/image_request.py`: form validation, image validation, and prompt composition.
- `backend/app/openai_images.py`: OpenAI image generation and editing wrapper.
- `backend/tests/`: backend unit tests.

## Data Flow

1. The user selects a tool from the homepage.
2. The tool page renders fields from the frontend tool registry.
3. The browser submits a `FormData` request to the FastAPI backend with the tool id, prompt, selected size, and optional uploaded image.
4. `POST /api/images/generate` validates the request.
5. The backend builds the OpenAI image request using the selected tool configuration.
6. OpenAI returns image data.
7. FastAPI returns `{ image: { src, mimeType, revisedPrompt } }` or `{ error }`.
8. The page renders the generated image and allows another generation.

Local development uses:

- Frontend: `http://localhost:3000`.
- Backend: `http://localhost:8000`.
- Frontend environment: `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`.

## OpenAI Integration

Use the OpenAI Python SDK from the FastAPI backend. The first implementation targets the GPT image model family and keeps the model name centralized in `OPENAI_IMAGE_MODEL`, defaulting to `gpt-image-2`.

Text-only generation is used for AI Image Creator. Image editing is used for restoration, avatar, and product-image flows when an uploaded image is present.

## Error Handling

The backend should return stable JSON errors for:

- Missing `OPENAI_API_KEY`.
- Unknown tool id.
- Empty prompt when a prompt is required.
- Missing image upload for tools that require an image.
- Unsupported file type.
- File too large.
- OpenAI API failures.

Server responses must not expose the API key or internal stack traces. The frontend displays these messages next to the form.

## UX Direction

The UI should feel like a focused creative utility rather than a generic SaaS landing page. The homepage should be immediately usable, with dense but polished tool cards and clear visual differentiation between creation, restoration, portrait, and product workflows.

Tool pages should keep the form and result area close together. The user should always understand what input is needed, when generation is running, and where the output will appear.

## Verification

Before considering the implementation complete:

- Confirm backend pytest passes.
- Confirm frontend lint and production build pass.
- Confirm each tool page renders.
- Confirm backend request validation catches missing prompt, missing image, unsupported file type, oversized file, unknown tool, and missing API key.
- With a valid `OPENAI_API_KEY`, run at least one real generation request through the FastAPI backend from the frontend.

