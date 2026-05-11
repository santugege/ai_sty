# Two Tool Image Prompt Design

Date: 2026-05-11

## Goal

Design the first version of the image prompt system around two clearly separated tools:

- ChatGPT general image conversation: pure text-to-image and image editing through natural language conversation.
- Product image generation: ecommerce product image generation from uploaded product images.

The two tools must share only generic image quality guidance. Product, platform, selling point, marketplace, and listing-specific logic must never leak into the ChatGPT general prompt.

## Current State

The repository currently has two image-related paths:

- `/api/agent/sessions` and `/api/agent/sessions/{session_id}/messages` drive the ChatGPT-style conversation flow.
- `/api/images/generate` drives the product image tool.

The product path already has product-specific prompt composition in `backend/app/image_request.py`. The ChatGPT conversation path currently asks a text model to return a JSON decision and then runs one image edit tool. That path does not yet support pure text-to-image when there is no current image.

## Prompt Architecture

Use a three-layer prompt composition model.

### Layer 1: Global Image Quality Prompt

Shared by both tools. This layer contains only universal image quality rules:

- Follow the user's explicit intent.
- Keep the main subject clear and visually coherent.
- Use stable composition, lighting, perspective, and material detail.
- Avoid low-resolution artifacts, warped anatomy, distorted objects, unwanted watermarks, unintended extra text, and illegible text.
- For edits, preserve all regions and visual details the user did not ask to change.
- When literal text is requested, keep it short, quote it exactly, and prioritize legibility.

This layer must not mention ecommerce, products, listings, platforms, marketplaces, selling points, promotions, or product packaging.

### Layer 2: Tool-Specific Prompt

Each tool owns a separate prompt.

#### ChatGPT General Image Prompt

Purpose:

- Handle pure text-to-image generation.
- Handle uploaded-image and current-image editing.
- Understand natural language requests in a multi-turn conversation.
- Ask a clarification question when the requested image action is too ambiguous.

Allowed concepts:

- User goal
- Scene
- Subject
- Style
- Composition
- Lighting
- Mood
- Camera/framing
- Reference image roles
- Preserve/change/avoid constraints
- Multi-turn continuity

Forbidden assumptions:

- Do not assume the image is a product photo.
- Do not assume ecommerce, listing, marketplace, platform style, selling points, or promotional copy.
- Do not invent brand or commercial constraints unless the user explicitly asks for them.

The planner should classify each turn into one of:

- `answer`: text-only answer or clarification.
- `generate`: create a new image from text.
- `edit`: edit the current or uploaded image.

For `generate`, no current image is required.

For `edit`, a current or uploaded image is required. The prompt must explicitly say what changes and what stays the same.

#### Product Image Prompt

Purpose:

- Generate ecommerce product visuals from uploaded product images.
- Preserve product identity and commercially important details.
- Apply platform, purpose, ratio, size, and user brief fields from the product workbench.

Required concepts:

- Product shape, logo, packaging, visible text, color, material, and identifying details must be preserved.
- Platform style may guide composition and commercial atmosphere.
- Image purpose may guide hierarchy and layout.
- Product category, selling points, scene style, visual tone, promotion text, preserve requirements, and avoid elements may guide the brief.

Allowed ecommerce concepts:

- Platform style
- Main image
- White-background image
- Scene image
- Promotion image
- Detail-page hero
- Selling points
- Commercial usability

This tool continues to require an uploaded product image.

### Layer 3: Request Brief

Every request adds a structured brief after the global and tool-specific prompt.

For ChatGPT general:

```json
{
  "mode": "generate | edit",
  "user_message": "...",
  "conversation_summary": "...",
  "recent_messages": [],
  "has_current_image": true,
  "uploaded_image_count": 0,
  "image_roles": [
    {
      "index": 1,
      "role": "current image | uploaded reference | style reference"
    }
  ],
  "size": "1536x1024",
  "quality": "high",
  "brief": {
    "user_goal": "...",
    "scene": "...",
    "subject": "...",
    "style": "...",
    "composition": "...",
    "lighting": "...",
    "preserve": [],
    "change": [],
    "avoid": []
  }
}
```

For product:

```json
{
  "mode": "product",
  "size": "1536x1024",
  "quality": "high",
  "aspect_ratio": "3:2",
  "image_count": 1,
  "platform_style": "...",
  "image_purpose": "...",
  "product_category": "...",
  "selling_points": "...",
  "scene_style": "...",
  "visual_tone": "...",
  "promotion_text": "...",
  "preserve_requirements": "...",
  "avoid_elements": "...",
  "additional_notes": "..."
}
```

## API And Service Behavior

### ChatGPT General Conversation

The ChatGPT conversation image service should support two image tools:

- `chatgpt_image_generate`: calls image generation without requiring an input image.
- `chatgpt_image_edit`: calls image editing with the current or uploaded image.

The planner may return:

```json
{
  "action": "answer",
  "assistant_message": "..."
}
```

```json
{
  "action": "generate",
  "assistant_message": "...",
  "tool_name": "chatgpt_image_generate",
  "tool_instruction": {
    "user_goal": "...",
    "scene": "...",
    "subject": "...",
    "style": "...",
    "composition": "...",
    "lighting": "...",
    "preserve": [],
    "change": [],
    "avoid": []
  }
}
```

```json
{
  "action": "edit",
  "assistant_message": "...",
  "tool_name": "chatgpt_image_edit",
  "tool_instruction": {
    "user_goal": "...",
    "scene": "...",
    "subject": "...",
    "style": "...",
    "composition": "...",
    "lighting": "...",
    "preserve": ["Keep all unmentioned regions unchanged."],
    "change": ["..."],
    "avoid": ["..."]
  }
}
```

If the user asks for an image without uploading one, `generate` must be valid. If the user asks to edit but no image exists, the assistant should answer with a request to upload an image.

### Product Image Tool

The product tool stays on `/api/images/generate` and keeps product-specific request fields. It can continue using `images.edit` because the uploaded product image is required.

## Quality Settings

First version should default generated output to `quality="high"` for both tools unless the UI later exposes draft/final quality. This favors quality over speed because the reported problem is poor image quality.

## Testing Requirements

Add tests that enforce prompt boundaries:

- ChatGPT general prompt does not contain ecommerce-specific words such as platform, marketplace, product listing, selling point, Pinduoduo, Taobao, Tmall, JD, Xiaohongshu, or Douyin.
- Product prompt contains product preservation rules and ecommerce-specific fields.
- ChatGPT planner accepts `generate`.
- ChatGPT service can generate an image without a current image.
- ChatGPT service still rejects edit when no current or uploaded image exists.
- ChatGPT image generate calls `images.generate`.
- ChatGPT image edit calls `images.edit`.
- Both image tools pass `quality="high"`.

## Open Decisions

- The first implementation can keep the existing two-step planner plus image API architecture, then migrate to Responses API image generation later.
- The first implementation should not redesign the frontend beyond any required action support and optional quality defaults.
- The first implementation should not add more tools beyond ChatGPT general and product.
