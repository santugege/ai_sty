# Product-Only Image Generation Design

## Goal

Keep only ecommerce product image generation in the frontend and backend. Remove the generic creator, photo restoration, and avatar tools from the product surface and backend registry.

## Approach

Preserve the existing API path, `POST /api/images/generate`, so the frontend request flow stays stable. Narrow both registries to the product tool, keep product-specific form fields and prompt composition, and make unknown or removed tool ids fail validation.

## Frontend

The homepage remains the product workbench entry. `frontend/src/lib/tools.ts` should expose only the `product` tool and product option registries. The dynamic tool route should either render the product workbench for `/tools/product` or return 404 for every other tool id. Generic tool UI components that only serve removed tools should be deleted when no remaining import uses them.

## Backend

`backend/app/tools.py` should define only `ToolId = "product"` and `image_tools = (product,)`. `validate_image_form` should continue to enforce product image upload and product platform/purpose validation through the existing product fields. Prompt composition should keep `compose_product_prompt` as the only live product path.

## Tests

Backend tests should assert that only the product tool is available, removed ids are rejected, product fields are required, and the FastAPI route passes product fields to the OpenAI wrapper. Frontend verification should cover lint/build and existing node tests.
