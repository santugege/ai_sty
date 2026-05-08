# Ecommerce Image Workbench Redesign

Date: 2026-05-08

## Goal

Redesign the current image toolbox into an ecommerce image workbench, starting from the frontend experience and extending the backend request model. The first redesign focuses on the Product Image Generator so users can create platform-specific product visuals through a realistic ecommerce workflow instead of a single generic prompt box.

The selected direction is a structured product image workbench:

- Keep the four existing tool entries.
- Make product image generation the primary experience.
- Add platform, purpose, category, selling point, scene, tone, promotion, preservation, and avoidance fields.
- Send structured product fields to the FastAPI backend.
- Let the backend validate the fields and compose a professional ecommerce prompt.

## Product Shape

The homepage remains a working toolbox, not a marketing landing page. Product image generation becomes the dominant entry point, while AI image creation, old photo restoration, and portrait generation remain supporting tools.

The product image flow should match a real ecommerce operator's task:

1. Upload a product image.
2. Select a platform style.
3. Select the image purpose.
4. Enter product category and core selling points.
5. Choose a scene style and visual tone.
6. Add optional promotion text.
7. Add preservation requirements and elements to avoid.
8. Select output size.
9. Submit the request and review the generated result.

## Platform Styles

The product workbench should include these platform styles:

- Pinduoduo: high-conversion, bright, promotional, strong selling point hierarchy, bold visual emphasis.
- Taobao and Tmall: polished marketplace presentation, clear product focus, balanced commercial atmosphere.
- JD: quality, trust, clean technical clarity, premium but practical presentation.
- Xiaohongshu: natural lifestyle scene, authentic seeding style, softer brand feel.
- Douyin ecommerce: energetic short-video commerce look, strong first-glance hook, bold rhythm.

Selecting a platform should change helper copy and recommended defaults in the frontend. The backend should also use the platform choice when composing the final prompt.

## Image Purposes

The product workbench should include these image purposes:

- Main image: product is dominant, clean hierarchy, strong first impression.
- White background image: clean product presentation suitable for listing or cutout use.
- Scene image: product placed in a realistic use environment.
- Promotion image: product plus campaign atmosphere and concise selling points.
- Detail hero image: first screen for a detail page, with richer context and layered information.

## Structured Fields

The frontend submits these product-specific fields as `FormData`:

- `platformStyle`
- `imagePurpose`
- `productCategory`
- `sellingPoints`
- `sceneStyle`
- `visualTone`
- `promotionText`
- `preserveRequirements`
- `avoidElements`

Existing fields remain:

- `toolId`
- `prompt`
- `size`
- `image`

For product requests, `image` is required. `prompt` becomes optional free-form notes rather than the main control surface.

## Backend Prompt Strategy

The backend composes the product prompt in layers:

1. Product preservation rules: keep product shape, color, logo, packaging structure, visible text, and important identifying details.
2. Ecommerce quality rules: avoid misleading claims, extra accessories, deformed packaging, fake labels, or changing the product identity.
3. Platform style rules from `platformStyle`.
4. Image purpose rules from `imagePurpose`.
5. User product details: category, selling points, scene, visual tone, promotion text, preservation requirements, avoid elements, and optional notes.

Non-product tools should continue using the existing prompt composition path.

## Frontend UX

The visual direction is a refined, dense ecommerce operations workbench. It should feel ready for repeated production work, not like a generic SaaS landing page.

Homepage:

- Product image generation gets a larger, richer entry area.
- The page surfaces platform style, image purpose, upload, and generation intent immediately.
- The other three tools remain visible as compact supporting cards.

Product page:

- Desktop layout uses a workbench composition: configuration on the left and center, result preview on the right.
- Mobile layout stacks the same workflow in a logical order.
- Use segmented controls, icon buttons, tag groups, text areas, and upload controls.
- Avoid a long plain form with only generic inputs.
- Keep current generation status, validation errors, and output preview close to the controls.

## Project Structure

Expected frontend changes:

- `frontend/src/app/page.tsx`: redesign homepage around ecommerce image workbench priority.
- `frontend/src/app/tools/[toolId]/page.tsx`: route product tool to a dedicated product workbench component.
- `frontend/src/components/product-workbench.tsx`: new product-specific workbench component.
- `frontend/src/components/tool-card.tsx`: visual refresh for supporting tools.
- `frontend/src/components/tool-form.tsx`: keep existing tools working and align styling.
- `frontend/src/lib/tools.ts`: add ecommerce platform, purpose, scene, tone, and default configuration.
- `frontend/src/app/globals.css`: update visual foundation and shared base styles.

Expected backend changes:

- `backend/app/main.py`: accept product-specific form fields.
- `backend/app/image_request.py`: validate and normalize product-specific fields.
- `backend/app/tools.py`: store product platform and purpose prompt rules.
- `backend/tests/test_image_request.py`: cover product field validation and prompt composition.
- `backend/tests/test_main.py`: cover route-level structured product field passing.

## Error Handling

The backend should keep stable JSON errors. Product-specific validation should return clear messages for invalid platform style, invalid image purpose, and missing required product image. Missing optional fields should not block generation.

The frontend should display backend errors beside the workbench controls and preserve the user's entered fields after a failed request.

## Verification

Before the redesign is considered complete:

- Product page renders the full structured workbench.
- Product workbench submits all structured fields to the backend.
- Backend prompt composition includes Pinduoduo and other platform style rules correctly.
- Existing creator, restoration, and avatar tools still submit successfully through the generic form.
- Backend tests pass.
- Frontend lint passes.
- Frontend production build passes.

