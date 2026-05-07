# Image Toolbox Website Design

Date: 2026-05-07

## Goal

Build a real image generation toolbox website powered by OpenAI image models. The first version should let users choose from several image tools, submit text and optional image uploads, and receive generated or edited images without exposing the OpenAI API key in the browser.

## Product Shape

The first screen is a toolbox, not a marketing landing page. Users choose one of four tools:

- AI Image Creator: generate an image from a text prompt.
- Old Photo Restoration: upload an old photo and request restoration such as scratch removal, color recovery, and blur improvement.
- Avatar and Portrait Generator: upload a reference image or describe a visual style to create an avatar or portrait.
- Product Image Generator: upload a product image and request a new background, scene, or ecommerce presentation.

Each tool has its own page, but the pages are driven by shared configuration so new tools can be added with low duplication.

## Architecture

Use Next.js App Router, TypeScript, and Tailwind CSS.

- Frontend: toolbox home page, tool detail pages, dynamic forms, upload controls, generation status, error messages, and image results.
- Backend: a Next.js API route at `/api/images/generate`.
- Configuration: a tool registry defines each tool's route, label, required fields, whether image upload is required, default prompt guidance, size options, and output defaults.
- Secrets: `OPENAI_API_KEY` is stored in server environment variables, such as `.env.local` during local development.

The frontend never receives or stores the OpenAI API key.

## Data Flow

1. The user selects a tool from the homepage.
2. The tool page renders fields from the tool registry.
3. The browser submits a `FormData` request with the tool id, prompt, selected size, and optional uploaded image.
4. `/api/images/generate` validates the request.
5. The server builds the OpenAI image request using the selected tool configuration.
6. OpenAI returns image data.
7. The API route returns a displayable result to the frontend.
8. The page renders the generated image and allows another generation.

## OpenAI Integration

Use the OpenAI Images API from the server route. The first implementation should target the GPT image model family and keep the model name centralized in one configuration value so it is easy to upgrade.

Text-only generation is used for AI Image Creator. Image editing is used for restoration, avatar, and product-image flows when an uploaded image is present.

## Error Handling

The app should display clear user-facing errors for:

- Missing `OPENAI_API_KEY`.
- Unknown tool id.
- Empty prompt when a prompt is required.
- Missing image upload for tools that require an image.
- Unsupported file type.
- File too large.
- OpenAI API failures.

Server responses must not expose the API key or internal stack traces.

## UX Direction

The UI should feel like a focused creative utility rather than a generic SaaS landing page. The homepage should be immediately usable, with dense but polished tool cards and clear visual differentiation between creation, restoration, portrait, and product workflows.

Tool pages should keep the form and result area close together. The user should always understand what input is needed, when generation is running, and where the output will appear.

## Verification

Before considering the implementation complete:

- Confirm TypeScript and production build pass.
- Confirm each tool page renders.
- Confirm request validation catches missing prompt, missing image, unsupported file type, and missing API key.
- With a valid `OPENAI_API_KEY`, run at least one real generation request.

