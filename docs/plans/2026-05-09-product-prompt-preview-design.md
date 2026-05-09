# Product Prompt Preview Design

## Goal

Adjust the product image generator so every generation starts from an uploaded original product image, and the right-side panel shows a read-only final prompt preview instead of an Agent conversation.

## Design

The product workbench remains a three-column production surface. The left column owns source image upload and generation settings. The upload control becomes required in both UI copy and submit behavior. The center column continues to show the generated image result. The right column becomes a prompt inspector: users type their natural-language requirement, then review the final composed prompt preview before generation.

The frontend builds a readable prompt preview from platform, image type, aspect ratio, output size, image count, required original-image preservation rules, and the user requirement. The submitted `prompt` field uses the same string. The backend still validates platform and image type, composes the authoritative OpenAI prompt, and now rejects product generation requests without an uploaded image by setting the product tool's `image_required` flag.

## Error Handling

If the user submits without an original image, the frontend returns a local error message and does not call the API. The backend also rejects missing product images with the existing `请上传商品图。` validation path, covering direct API calls.

## Testing

Backend tests cover the required upload behavior and product tool configuration. Frontend source-level tests cover the removal of Agent conversation state/copy, the presence of a read-only prompt preview, required upload messaging, and the use of the user requirement in the generated prompt.
