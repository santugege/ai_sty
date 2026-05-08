# Ecommerce Image Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the existing image toolbox into an ecommerce image workbench with a structured Product Image Generator flow and backend prompt composition for platform-specific product visuals.

**Architecture:** Keep the current Next.js frontend and FastAPI backend split. Add product-specific option registries on both sides, submit structured product fields through `FormData`, validate and normalize those fields in the backend, and compose product prompts from platform, purpose, category, selling points, scene, tone, promotion, preservation, and avoidance data. Existing non-product tools continue using the generic form and prompt path.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind CSS, lucide-react, FastAPI, OpenAI Python SDK, pytest.

---

## File Structure

- Modify `backend/app/tools.py`: keep the existing `ImageTool` registry and add product platform and image purpose prompt rule registries.
- Modify `backend/app/image_request.py`: add `ProductImageFields`, validate product-specific fields, and compose layered ecommerce prompts.
- Modify `backend/app/main.py`: accept product-specific `FormData` fields and pass them to validation.
- Modify `backend/app/openai_images.py`: pass structured product fields into prompt composition.
- Modify `backend/tests/test_tools.py`: test product platform and purpose registries.
- Modify `backend/tests/test_image_request.py`: test product field validation and product prompt composition.
- Modify `backend/tests/test_main.py`: test route-level product field passing.
- Create `frontend/src/lib/image-api.ts`: shared frontend API helper for submitting image generation requests.
- Modify `frontend/src/lib/tools.ts`: add ecommerce frontend option registries and refresh product tool metadata.
- Modify `frontend/src/components/tool-form.tsx`: use the shared image API helper while preserving existing generic tool behavior.
- Create `frontend/src/components/product-workbench.tsx`: dedicated structured product image workbench.
- Modify `frontend/src/app/tools/[toolId]/page.tsx`: render `ProductWorkbench` for the product tool and `ToolForm` for the other tools.
- Modify `frontend/src/app/page.tsx`: redesign the homepage around the ecommerce workbench priority.
- Modify `frontend/src/components/tool-card.tsx`: refresh supporting tool cards to fit the new direction.
- Modify `frontend/src/app/globals.css`: update the visual foundation and shared base styles.

---

### Task 1: Backend Product Option Registry

**Files:**
- Modify: `backend/app/tools.py`
- Modify: `backend/tests/test_tools.py`

- [ ] **Step 1: Write failing registry tests**

Append these tests to `backend/tests/test_tools.py`:

```python
from app.tools import (
    get_product_image_purpose,
    get_product_platform_style,
    product_image_purposes,
    product_platform_styles,
)


def test_defines_product_platform_styles_in_display_order():
    assert [style.id for style in product_platform_styles] == [
        "pinduoduo",
        "taobao-tmall",
        "jd",
        "xiaohongshu",
        "douyin",
    ]
    assert get_product_platform_style("pinduoduo").label == "拼多多"
    assert "high-conversion" in get_product_platform_style("pinduoduo").prompt
    assert get_product_platform_style("missing") is None


def test_defines_product_image_purposes_in_display_order():
    assert [purpose.id for purpose in product_image_purposes] == [
        "main-image",
        "white-background",
        "scene-image",
        "promotion-image",
        "detail-hero",
    ]
    assert get_product_image_purpose("promotion-image").label == "促销图"
    assert "campaign" in get_product_image_purpose("promotion-image").prompt
    assert get_product_image_purpose("missing") is None
```

- [ ] **Step 2: Run registry tests to verify failure**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_tools.py -q
```

Expected: FAIL with an import error for `product_platform_styles` or related helper names.

- [ ] **Step 3: Add product rule registries**

Modify `backend/app/tools.py` so the top-level type and dataclass section contains these additions after `ToolId`:

```python
ProductPlatformStyleId = Literal[
    "pinduoduo",
    "taobao-tmall",
    "jd",
    "xiaohongshu",
    "douyin",
]
ProductImagePurposeId = Literal[
    "main-image",
    "white-background",
    "scene-image",
    "promotion-image",
    "detail-hero",
]


@dataclass(frozen=True)
class ProductPromptRule:
    id: str
    label: str
    prompt: str
```

Add these registries after `image_sizes`:

```python
product_platform_styles: tuple[ProductPromptRule, ...] = (
    ProductPromptRule(
        id="pinduoduo",
        label="拼多多",
        prompt=(
            "Use a high-conversion Pinduoduo ecommerce style: bright lighting, "
            "bold product hierarchy, clear promotional energy, strong selling "
            "point emphasis, and an immediately understandable value offer."
        ),
    ),
    ProductPromptRule(
        id="taobao-tmall",
        label="淘宝/天猫",
        prompt=(
            "Use a polished Taobao and Tmall marketplace style: refined product "
            "presentation, clear visual hierarchy, commercial but tasteful scene "
            "design, and balanced brand atmosphere."
        ),
    ),
    ProductPromptRule(
        id="jd",
        label="京东",
        prompt=(
            "Use a JD ecommerce style: trustworthy, clean, quality-focused, "
            "technically clear, premium but practical, with a strong sense of "
            "authentic product information."
        ),
    ),
    ProductPromptRule(
        id="xiaohongshu",
        label="小红书",
        prompt=(
            "Use a Xiaohongshu lifestyle commerce style: natural, authentic, "
            "softly aspirational, realistic use context, tactile textures, and "
            "a believable recommendation feeling."
        ),
    ),
    ProductPromptRule(
        id="douyin",
        label="抖音电商",
        prompt=(
            "Use a Douyin ecommerce style: energetic, first-glance hook, bold "
            "rhythm, short-video commerce impact, vivid contrast, and a clear "
            "reason to stop scrolling."
        ),
    ),
)

product_image_purposes: tuple[ProductPromptRule, ...] = (
    ProductPromptRule(
        id="main-image",
        label="主图",
        prompt=(
            "Create a main listing image where the product is dominant, the "
            "background supports conversion, and the first impression is clear "
            "within one second."
        ),
    ),
    ProductPromptRule(
        id="white-background",
        label="白底图",
        prompt=(
            "Create a clean white-background product image suitable for listings "
            "or cutout workflows. Keep edges crisp and avoid decorative clutter."
        ),
    ),
    ProductPromptRule(
        id="scene-image",
        label="场景图",
        prompt=(
            "Create a realistic scene image that places the product in a believable "
            "use environment while keeping the product as the clear subject."
        ),
    ),
    ProductPromptRule(
        id="promotion-image",
        label="促销图",
        prompt=(
            "Create a campaign-oriented promotional image with concise selling "
            "point hierarchy, energetic composition, and visual space for offer "
            "or campaign text."
        ),
    ),
    ProductPromptRule(
        id="detail-hero",
        label="详情页首屏",
        prompt=(
            "Create a detail page hero image with richer context, layered visual "
            "information, clear product benefit storytelling, and premium layout."
        ),
    ),
)
```

Add these helper functions after `get_tool_by_id`:

```python
def get_product_platform_style(style_id: str) -> ProductPromptRule | None:
    return next(
        (style for style in product_platform_styles if style.id == style_id),
        None,
    )


def get_product_image_purpose(purpose_id: str) -> ProductPromptRule | None:
    return next(
        (purpose for purpose in product_image_purposes if purpose.id == purpose_id),
        None,
    )
```

- [ ] **Step 4: Run registry tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_tools.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit backend registries**

Run:

```bash
rtk git add backend/app/tools.py backend/tests/test_tools.py
rtk git commit -m "feat: add ecommerce product prompt registries"
```

Expected: commit succeeds.

---

### Task 2: Backend Product Validation and Prompt Composition

**Files:**
- Modify: `backend/app/image_request.py`
- Modify: `backend/tests/test_image_request.py`

- [ ] **Step 1: Write failing validation and prompt tests**

Update the import block in `backend/tests/test_image_request.py`:

```python
from app.image_request import (
    MAX_IMAGE_BYTES,
    SUPPORTED_IMAGE_TYPES,
    ImageRequestError,
    ProductImageFields,
    compose_tool_prompt,
    validate_image_form,
)
```

Append these tests to `backend/tests/test_image_request.py`:

```python
def test_product_request_normalizes_structured_fields():
    result = run(
        validate_image_form(
            "product",
            "  保持瓶身居中  ",
            "1536x1024",
            upload_file(content_type="image/png", filename="product.png"),
            "key",
            platform_style="pinduoduo",
            image_purpose="promotion-image",
            product_category="  小家电  ",
            selling_points="  三档风力，静音，USB 充电  ",
            scene_style="夏季桌面",
            visual_tone="高转化促销",
            promotion_text="限时立减 20 元",
            preserve_requirements="保留品牌 logo",
            avoid_elements="不要额外配件",
        )
    )

    assert result.tool.id == "product"
    assert result.prompt == "保持瓶身居中"
    assert result.product_fields == ProductImageFields(
        platform_style="pinduoduo",
        image_purpose="promotion-image",
        product_category="小家电",
        selling_points="三档风力，静音，USB 充电",
        scene_style="夏季桌面",
        visual_tone="高转化促销",
        promotion_text="限时立减 20 元",
        preserve_requirements="保留品牌 logo",
        avoid_elements="不要额外配件",
    )


def test_product_request_rejects_invalid_platform_style():
    try:
        run(
            validate_image_form(
                "product",
                "",
                "1536x1024",
                upload_file(),
                "key",
                platform_style="missing",
                image_purpose="main-image",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请选择有效的平台风格。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_product_request_rejects_invalid_image_purpose():
    try:
        run(
            validate_image_form(
                "product",
                "",
                "1536x1024",
                upload_file(),
                "key",
                platform_style="pinduoduo",
                image_purpose="missing",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请选择有效的图片用途。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_non_product_request_ignores_product_fields():
    result = run(
        validate_image_form(
            "restore",
            "修复划痕",
            "1024x1024",
            upload_file(),
            "key",
            platform_style="pinduoduo",
            image_purpose="promotion-image",
            product_category="小家电",
        )
    )

    assert result.tool.id == "restore"
    assert result.product_fields is None


def test_compose_product_prompt_uses_structured_ecommerce_fields():
    tool = get_tool_by_id("product")
    prompt = compose_tool_prompt(
        tool,
        "保留瓶身居中",
        ProductImageFields(
            platform_style="pinduoduo",
            image_purpose="promotion-image",
            product_category="小家电",
            selling_points="三档风力，静音，USB 充电",
            scene_style="夏季桌面",
            visual_tone="高转化促销",
            promotion_text="限时立减 20 元",
            preserve_requirements="保留品牌 logo",
            avoid_elements="不要额外配件",
        ),
    )

    assert tool.base_prompt in prompt
    assert "Product preservation rules:" in prompt
    assert "Platform style (拼多多):" in prompt
    assert "high-conversion Pinduoduo" in prompt
    assert "Image purpose (促销图):" in prompt
    assert "Product category: 小家电" in prompt
    assert "Selling points: 三档风力，静音，USB 充电" in prompt
    assert "Promotion text: 限时立减 20 元" in prompt
    assert "Avoid elements: 不要额外配件" in prompt
    assert "Additional notes: 保留瓶身居中" in prompt
```

- [ ] **Step 2: Run image request tests to verify failure**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_request.py -q
```

Expected: FAIL because `ProductImageFields` and the new keyword parameters do not exist.

- [ ] **Step 3: Implement product fields and validation**

Modify the import in `backend/app/image_request.py`:

```python
from typing import cast

from app.tools import (
    ImageSize,
    ImageTool,
    ProductImagePurposeId,
    ProductPlatformStyleId,
    get_product_image_purpose,
    get_product_platform_style,
    get_tool_by_id,
)
```

Add `ProductImageFields` after `ImageRequestError`:

```python
@dataclass(frozen=True)
class ProductImageFields:
    platform_style: ProductPlatformStyleId
    image_purpose: ProductImagePurposeId
    product_category: str = ""
    selling_points: str = ""
    scene_style: str = ""
    visual_tone: str = ""
    promotion_text: str = ""
    preserve_requirements: str = ""
    avoid_elements: str = ""
```

Add `product_fields` to `ValidImageRequest`:

```python
@dataclass(frozen=True)
class ValidImageRequest:
    tool: ImageTool
    prompt: str
    size: ImageSize
    image_bytes: bytes | None = None
    image_name: str | None = None
    image_type: str | None = None
    product_fields: ProductImageFields | None = None
```

Change the `validate_image_form` signature to:

```python
async def validate_image_form(
    tool_id: str | None,
    prompt: str | None,
    size: str | None,
    image: UploadFile | None,
    api_key: str | None,
    *,
    platform_style: str | None = None,
    image_purpose: str | None = None,
    product_category: str | None = None,
    selling_points: str | None = None,
    scene_style: str | None = None,
    visual_tone: str | None = None,
    promotion_text: str | None = None,
    preserve_requirements: str | None = None,
    avoid_elements: str | None = None,
) -> ValidImageRequest:
```

Before the `return ValidImageRequest(...)` block, add:

```python
    product_fields = validate_product_fields(
        tool,
        platform_style=platform_style,
        image_purpose=image_purpose,
        product_category=product_category,
        selling_points=selling_points,
        scene_style=scene_style,
        visual_tone=visual_tone,
        promotion_text=promotion_text,
        preserve_requirements=preserve_requirements,
        avoid_elements=avoid_elements,
    )
```

Include `product_fields=product_fields` in the returned `ValidImageRequest`.

Add these helper functions below `validate_image_form`:

```python
def validate_product_fields(
    tool: ImageTool,
    *,
    platform_style: str | None,
    image_purpose: str | None,
    product_category: str | None,
    selling_points: str | None,
    scene_style: str | None,
    visual_tone: str | None,
    promotion_text: str | None,
    preserve_requirements: str | None,
    avoid_elements: str | None,
) -> ProductImageFields | None:
    if tool.id != "product":
        return None

    normalized_platform_style = normalize_text(platform_style)
    normalized_image_purpose = normalize_text(image_purpose)

    platform_rule = get_product_platform_style(normalized_platform_style)
    if platform_rule is None:
        raise ImageRequestError(400, "请选择有效的平台风格。")

    purpose_rule = get_product_image_purpose(normalized_image_purpose)
    if purpose_rule is None:
        raise ImageRequestError(400, "请选择有效的图片用途。")

    return ProductImageFields(
        platform_style=cast(ProductPlatformStyleId, platform_rule.id),
        image_purpose=cast(ProductImagePurposeId, purpose_rule.id),
        product_category=normalize_text(product_category),
        selling_points=normalize_text(selling_points),
        scene_style=normalize_text(scene_style),
        visual_tone=normalize_text(visual_tone),
        promotion_text=normalize_text(promotion_text),
        preserve_requirements=normalize_text(preserve_requirements),
        avoid_elements=normalize_text(avoid_elements),
    )


def normalize_text(value: str | None) -> str:
    return (value or "").strip()
```

- [ ] **Step 4: Implement product prompt composition**

Replace `compose_tool_prompt` in `backend/app/image_request.py` with:

```python
def compose_tool_prompt(
    tool: ImageTool,
    user_prompt: str,
    product_fields: ProductImageFields | None = None,
) -> str:
    normalized_prompt = user_prompt.strip()

    if tool.id == "product" and product_fields is not None:
        return compose_product_prompt(tool, normalized_prompt, product_fields)

    if not normalized_prompt:
        return tool.base_prompt

    return f"{tool.base_prompt}\n\nUser request:\n{normalized_prompt}"
```

Add this helper below it:

```python
def compose_product_prompt(
    tool: ImageTool,
    user_prompt: str,
    product_fields: ProductImageFields,
) -> str:
    platform_rule = get_product_platform_style(product_fields.platform_style)
    purpose_rule = get_product_image_purpose(product_fields.image_purpose)

    if platform_rule is None:
        raise ImageRequestError(400, "请选择有效的平台风格。")

    if purpose_rule is None:
        raise ImageRequestError(400, "请选择有效的图片用途。")

    sections = [
        tool.base_prompt,
        (
            "Product preservation rules:\n"
            "- Preserve the uploaded product's shape, color, logo, package "
            "structure, visible text, material cues, and identifying details.\n"
            "- Do not invent extra accessories, fake labels, misleading claims, "
            "or features not visible or described by the user.\n"
            "- Keep the product commercially usable and avoid visual deformation."
        ),
        f"Platform style ({platform_rule.label}):\n{platform_rule.prompt}",
        f"Image purpose ({purpose_rule.label}):\n{purpose_rule.prompt}",
    ]

    brief_lines = build_product_brief_lines(product_fields, user_prompt)
    if brief_lines:
        sections.append("User product brief:\n" + "\n".join(brief_lines))

    return "\n\n".join(sections)


def build_product_brief_lines(
    product_fields: ProductImageFields,
    user_prompt: str,
) -> list[str]:
    field_lines = [
        ("Product category", product_fields.product_category),
        ("Selling points", product_fields.selling_points),
        ("Scene style", product_fields.scene_style),
        ("Visual tone", product_fields.visual_tone),
        ("Promotion text", product_fields.promotion_text),
        ("Preserve requirements", product_fields.preserve_requirements),
        ("Avoid elements", product_fields.avoid_elements),
        ("Additional notes", user_prompt),
    ]

    return [f"- {label}: {value}" for label, value in field_lines if value]
```

- [ ] **Step 5: Run image request tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_request.py -q
```

Expected: PASS.

- [ ] **Step 6: Run all backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 7: Commit validation and prompt composition**

Run:

```bash
rtk git add backend/app/image_request.py backend/tests/test_image_request.py
rtk git commit -m "feat: compose structured ecommerce product prompts"
```

Expected: commit succeeds.

---

### Task 3: Backend Route and OpenAI Prompt Handoff

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/openai_images.py`
- Modify: `backend/tests/test_main.py`
- Modify: `backend/tests/test_openai_images.py`

- [ ] **Step 1: Write failing route test for product fields**

Append this test to `backend/tests/test_main.py`:

```python
def test_image_route_passes_product_fields_to_openai_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    captured_request = {}

    def fake_request_image_from_openai(valid_request, api_key, model):
        captured_request["valid_request"] = valid_request
        return GeneratedImageResult(src="data:image/png;base64,product")

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={
            "toolId": "product",
            "prompt": "保留瓶身居中",
            "size": "1536x1024",
            "platformStyle": "pinduoduo",
            "imagePurpose": "promotion-image",
            "productCategory": "小家电",
            "sellingPoints": "三档风力，静音，USB 充电",
            "sceneStyle": "夏季桌面",
            "visualTone": "高转化促销",
            "promotionText": "限时立减 20 元",
            "preserveRequirements": "保留品牌 logo",
            "avoidElements": "不要额外配件",
        },
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    valid_request = captured_request["valid_request"]
    assert valid_request.tool.id == "product"
    assert valid_request.product_fields.platform_style == "pinduoduo"
    assert valid_request.product_fields.image_purpose == "promotion-image"
    assert valid_request.product_fields.product_category == "小家电"
```

- [ ] **Step 2: Write failing OpenAI prompt handoff test**

Append this test to `backend/tests/test_openai_images.py`:

```python
from app.image_request import ProductImageFields


def test_requests_image_edit_with_structured_product_prompt():
    class FakeImages:
        def __init__(self):
            self.edit_kwargs = None

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "product"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("product"),
            prompt="保留瓶身居中",
            size="1536x1024",
            image_bytes=b"image-bytes",
            image_name="product.png",
            image_type="image/png",
            product_fields=ProductImageFields(
                platform_style="pinduoduo",
                image_purpose="promotion-image",
                product_category="小家电",
                selling_points="三档风力",
            ),
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.src == "data:image/png;base64,product"
    assert "Platform style (拼多多):" in fake_client.images.edit_kwargs["prompt"]
    assert "Product category: 小家电" in fake_client.images.edit_kwargs["prompt"]
```

If `backend/tests/test_openai_images.py` already imports `ProductImageFields`, keep a single import.

- [ ] **Step 3: Run backend tests to verify failure**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_main.py backend/tests/test_openai_images.py -q
```

Expected: FAIL because the route does not accept the new form fields and `openai_images.py` does not pass `product_fields`.

- [ ] **Step 4: Accept product form fields in FastAPI route**

Change the route signature in `backend/app/main.py`:

```python
@app.post("/api/images/generate")
async def generate_image(
    toolId: str = Form(...),
    prompt: str = Form(""),
    size: str = Form(""),
    platformStyle: str = Form(""),
    imagePurpose: str = Form(""),
    productCategory: str = Form(""),
    sellingPoints: str = Form(""),
    sceneStyle: str = Form(""),
    visualTone: str = Form(""),
    promotionText: str = Form(""),
    preserveRequirements: str = Form(""),
    avoidElements: str = Form(""),
    image: UploadFile | None = File(None),
):
```

Change the validation call:

```python
        valid_request = await validate_image_form(
            toolId,
            prompt,
            size,
            image,
            api_key,
            platform_style=platformStyle,
            image_purpose=imagePurpose,
            product_category=productCategory,
            selling_points=sellingPoints,
            scene_style=sceneStyle,
            visual_tone=visualTone,
            promotion_text=promotionText,
            preserve_requirements=preserveRequirements,
            avoid_elements=avoidElements,
        )
```

- [ ] **Step 5: Pass product fields into OpenAI prompt composition**

Change this line in `backend/app/openai_images.py`:

```python
    prompt = compose_tool_prompt(request.tool, request.prompt)
```

to:

```python
    prompt = compose_tool_prompt(
        request.tool,
        request.prompt,
        request.product_fields,
    )
```

- [ ] **Step 6: Run backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 7: Commit route and prompt handoff**

Run:

```bash
rtk git add backend/app/main.py backend/app/openai_images.py backend/tests/test_main.py backend/tests/test_openai_images.py
rtk git commit -m "feat: accept ecommerce product fields"
```

Expected: commit succeeds.

---

### Task 4: Frontend Ecommerce Config and Shared API Helper

**Files:**
- Create: `frontend/src/lib/image-api.ts`
- Modify: `frontend/src/lib/tools.ts`
- Modify: `frontend/src/components/tool-form.tsx`

- [ ] **Step 1: Create shared image API helper**

Write `frontend/src/lib/image-api.ts`:

```ts
import type { ImageSize } from "@/lib/tools";

export type GeneratedImage = {
  src: string;
  mimeType: string;
  revisedPrompt?: string | null;
};

type ImageGenerationPayload = {
  image?: GeneratedImage;
  error?: string;
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export const genericErrorMessage = "图片生成失败，请稍后重试。";

export function getImageDimensions(size: ImageSize) {
  const [width, height] = size.split("x").map(Number) as [number, number];

  return { width, height };
}

export async function submitImageGenerationForm(
  formData: FormData,
): Promise<GeneratedImage> {
  const response = await fetch(`${apiBaseUrl}/api/images/generate`, {
    method: "POST",
    body: formData,
  });
  const payload = await readImageGenerationPayload(response);

  if (!response.ok || !payload.image) {
    throw new Error(payload.error || genericErrorMessage);
  }

  return payload.image;
}

async function readImageGenerationPayload(
  response: Response,
): Promise<ImageGenerationPayload> {
  const contentType = response.headers.get("content-type")?.toLowerCase();

  if (!contentType?.includes("json")) {
    return {};
  }

  try {
    return (await response.json()) as ImageGenerationPayload;
  } catch {
    return {};
  }
}
```

- [ ] **Step 2: Add frontend ecommerce option registries**

In `frontend/src/lib/tools.ts`, add these types and arrays after the existing `ImageTool` type:

```ts
export type ProductPlatformStyleId =
  | "pinduoduo"
  | "taobao-tmall"
  | "jd"
  | "xiaohongshu"
  | "douyin";

export type ProductImagePurposeId =
  | "main-image"
  | "white-background"
  | "scene-image"
  | "promotion-image"
  | "detail-hero";

export type ProductSceneStyleId =
  | "studio"
  | "home"
  | "outdoor"
  | "gift"
  | "festival";

export type ProductVisualToneId =
  | "conversion"
  | "premium"
  | "lifestyle"
  | "minimal"
  | "vibrant";

export type ProductOption<TId extends string = string> = {
  id: TId;
  label: string;
  description: string;
};

export const productPlatformStyles: ProductOption<ProductPlatformStyleId>[] = [
  {
    id: "pinduoduo",
    label: "拼多多",
    description: "高转化、强促销、卖点醒目，适合快速抓住价格和利益点。",
  },
  {
    id: "taobao-tmall",
    label: "淘宝/天猫",
    description: "精致电商质感，商品主体清晰，兼顾品牌感和转化。",
  },
  {
    id: "jd",
    label: "京东",
    description: "品质可信、参数清楚、画面干净，突出专业和可靠。",
  },
  {
    id: "xiaohongshu",
    label: "小红书",
    description: "生活方式种草感，自然真实，适合内容化商品展示。",
  },
  {
    id: "douyin",
    label: "抖音电商",
    description: "强节奏、强钩子、短视频货架感，第一眼更有冲击。",
  },
];

export const productImagePurposes: ProductOption<ProductImagePurposeId>[] = [
  {
    id: "main-image",
    label: "主图",
    description: "商品主体最大化，第一眼说明卖什么、为什么值得点。",
  },
  {
    id: "white-background",
    label: "白底图",
    description: "干净白底，适合商品列表、审核、抠图和基础素材。",
  },
  {
    id: "scene-image",
    label: "场景图",
    description: "把商品放进真实使用环境，强调氛围和使用想象。",
  },
  {
    id: "promotion-image",
    label: "促销图",
    description: "突出活动气氛和核心卖点，预留促销文案表达空间。",
  },
  {
    id: "detail-hero",
    label: "详情页首屏",
    description: "适合详情页开头，信息层级更丰富，强化商品价值。",
  },
];

export const productSceneStyles: ProductOption<ProductSceneStyleId>[] = [
  { id: "studio", label: "纯色棚拍", description: "干净、可控、突出主体。" },
  { id: "home", label: "居家生活", description: "真实日常环境，适合种草。" },
  { id: "outdoor", label: "户外使用", description: "强调便携、耐用和场景感。" },
  { id: "gift", label: "礼盒陈列", description: "适合节日、送礼和套装表达。" },
  { id: "festival", label: "节日活动", description: "更强活动氛围和购买冲动。" },
];

export const productVisualTones: ProductOption<ProductVisualToneId>[] = [
  { id: "conversion", label: "高转化促销", description: "明亮、直接、利益点突出。" },
  { id: "premium", label: "品质轻奢", description: "克制、高级、强调质感。" },
  { id: "lifestyle", label: "真实种草", description: "自然光、生活化、可信赖。" },
  { id: "minimal", label: "简约白净", description: "留白充分，适合干净主图。" },
  { id: "vibrant", label: "鲜明活力", description: "色彩更强，适合短视频货架。" },
];
```

Update the product tool in `imageTools`:

```ts
  {
    id: "product",
    title: "电商商品图工作台",
    eyebrow: "Ecommerce workbench",
    description: "按平台、用途、卖点和场景生成更贴近真实运营需求的商品图。",
    mode: "edit",
    icon: "package",
    accent: "gold",
    promptLabel: "补充说明",
    promptPlaceholder:
      "例如：保留瓶身居中，包装文字清晰，不要改变瓶盖颜色",
    promptRequired: false,
    imageRequired: true,
    imageLabel: "上传商品原图",
    defaultSize: "1536x1024",
    sizeOptions: [...imageSizes],
    examples: ["拼多多主图", "白底商品图", "小红书场景图", "详情页首屏"],
  },
```

- [ ] **Step 3: Refactor generic tool form to use shared API helper**

In `frontend/src/components/tool-form.tsx`, remove local definitions for `GeneratedImage`, `ImageGenerationPayload`, `apiBaseUrl`, `genericErrorMessage`, `getImageDimensions`, and `readImageGenerationPayload`.

Add this import:

```ts
import {
  genericErrorMessage,
  getImageDimensions,
  submitImageGenerationForm,
  type GeneratedImage,
} from "@/lib/image-api";
```

Replace the `fetch` block in `handleSubmit` with:

```ts
    try {
      const generatedImage = await submitImageGenerationForm(formData);

      setResultSize(size);
      setResult(generatedImage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : genericErrorMessage);
    } finally {
      submitLockRef.current = false;
      setIsSubmitting(false);
    }
```

- [ ] **Step 4: Run frontend lint**

Run:

```bash
rtk npm run lint --prefix frontend
```

Expected: PASS.

- [ ] **Step 5: Commit frontend config and API helper**

Run:

```bash
rtk git add frontend/src/lib/image-api.ts frontend/src/lib/tools.ts frontend/src/components/tool-form.tsx
rtk git commit -m "feat: add ecommerce frontend configuration"
```

Expected: commit succeeds.

---

### Task 5: Product Workbench Component and Route Integration

**Files:**
- Create: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/src/app/tools/[toolId]/page.tsx`

- [ ] **Step 1: Create product workbench component**

Write `frontend/src/components/product-workbench.tsx`:

```tsx
"use client";

import Image from "next/image";
import { useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  BadgePercent,
  Boxes,
  ImageIcon,
  Loader2,
  PackageOpen,
  Sparkles,
  Upload,
} from "lucide-react";
import {
  imageSizes,
  productImagePurposes,
  productPlatformStyles,
  productSceneStyles,
  productVisualTones,
  type ImageSize,
  type ImageTool,
  type ProductImagePurposeId,
  type ProductPlatformStyleId,
  type ProductSceneStyleId,
  type ProductVisualToneId,
} from "@/lib/tools";
import {
  genericErrorMessage,
  getImageDimensions,
  submitImageGenerationForm,
  type GeneratedImage,
} from "@/lib/image-api";

type ProductWorkbenchProps = {
  tool: ImageTool;
};

function classNames(...values: Array<string | false>) {
  return values.filter(Boolean).join(" ");
}

export function ProductWorkbench({ tool }: ProductWorkbenchProps) {
  const [platformStyle, setPlatformStyle] =
    useState<ProductPlatformStyleId>("pinduoduo");
  const [imagePurpose, setImagePurpose] =
    useState<ProductImagePurposeId>("promotion-image");
  const [sceneStyle, setSceneStyle] = useState<ProductSceneStyleId>("studio");
  const [visualTone, setVisualTone] =
    useState<ProductVisualToneId>("conversion");
  const [productCategory, setProductCategory] = useState("");
  const [sellingPoints, setSellingPoints] = useState("");
  const [promotionText, setPromotionText] = useState("");
  const [preserveRequirements, setPreserveRequirements] = useState(
    "保留商品外观、品牌 logo、包装结构和可见文字",
  );
  const [avoidElements, setAvoidElements] = useState(
    "不要额外配件、虚假价格、夸大功效或改变包装颜色",
  );
  const [notes, setNotes] = useState("");
  const [size, setSize] = useState<ImageSize>(tool.defaultSize);
  const [resultSize, setResultSize] = useState<ImageSize>(tool.defaultSize);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GeneratedImage | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submitLockRef = useRef(false);

  const selectedPlatform = productPlatformStyles.find(
    (option) => option.id === platformStyle,
  );
  const selectedPurpose = productImagePurposes.find(
    (option) => option.id === imagePurpose,
  );
  const selectedScene = productSceneStyles.find(
    (option) => option.id === sceneStyle,
  );
  const selectedTone = productVisualTones.find(
    (option) => option.id === visualTone,
  );
  const previewDimensions = useMemo(
    () => getImageDimensions(resultSize),
    [resultSize],
  );
  const fileLabel = file?.name || "上传 PNG、JPG 或 WebP 商品原图";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submitLockRef.current) {
      return;
    }

    submitLockRef.current = true;
    setError("");
    setResult(null);
    setIsSubmitting(true);

    const formData = new FormData();
    formData.append("toolId", tool.id);
    formData.append("prompt", notes);
    formData.append("size", size);
    formData.append("platformStyle", platformStyle);
    formData.append("imagePurpose", imagePurpose);
    formData.append("productCategory", productCategory);
    formData.append("sellingPoints", sellingPoints);
    formData.append("sceneStyle", selectedScene?.label || sceneStyle);
    formData.append("visualTone", selectedTone?.label || visualTone);
    formData.append("promotionText", promotionText);
    formData.append("preserveRequirements", preserveRequirements);
    formData.append("avoidElements", avoidElements);

    if (file) {
      formData.append("image", file);
    }

    try {
      const generatedImage = await submitImageGenerationForm(formData);

      setResultSize(size);
      setResult(generatedImage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : genericErrorMessage);
    } finally {
      submitLockRef.current = false;
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(18rem,0.68fr)_minmax(22rem,0.82fr)_minmax(24rem,1fr)]">
      <form onSubmit={handleSubmit} className="contents">
        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-amber-100 text-amber-800">
              <PackageOpen aria-hidden="true" className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-950">商品素材</h2>
              <p className="text-sm leading-6 text-zinc-500">
                先上传商品原图，再补齐运营信息。
              </p>
            </div>
          </div>

          <label
            htmlFor="product-image"
            className={classNames(
              "mt-5 block",
              isSubmitting && "cursor-not-allowed opacity-70",
            )}
          >
            <span className="text-sm font-semibold text-zinc-900">
              上传商品原图
            </span>
            <span className="mt-3 flex min-h-32 items-center gap-3 rounded-md border border-dashed border-zinc-300 bg-zinc-50 px-4 py-4 text-zinc-600 transition hover:border-zinc-950">
              <Upload aria-hidden="true" className="h-5 w-5 shrink-0" />
              <span className="min-w-0 truncate">{fileLabel}</span>
            </span>
            <input
              id="product-image"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              required
              disabled={isSubmitting}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>

          <label className="mt-5 block text-sm font-semibold text-zinc-900">
            商品类目
            <input
              value={productCategory}
              onChange={(event) => setProductCategory(event.target.value)}
              placeholder="例如：小家电、美妆、食品、服饰"
              disabled={isSubmitting}
              className="mt-2 w-full rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>

          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            核心卖点
            <textarea
              value={sellingPoints}
              onChange={(event) => setSellingPoints(event.target.value)}
              placeholder="例如：三档风力、静音、USB 充电、宿舍可用"
              rows={4}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>

          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            输出尺寸
            <select
              value={size}
              onChange={(event) => setSize(event.target.value as ImageSize)}
              disabled={isSubmitting}
              className="mt-2 w-full rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            >
              {imageSizes.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-rose-100 text-rose-700">
              <BadgePercent aria-hidden="true" className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-950">运营策略</h2>
              <p className="text-sm leading-6 text-zinc-500">
                平台和用途会决定画面重点。
              </p>
            </div>
          </div>

          <OptionGroup
            title="平台风格"
            value={platformStyle}
            options={productPlatformStyles}
            onChange={(value) => setPlatformStyle(value)}
            disabled={isSubmitting}
          />

          <OptionGroup
            title="图片用途"
            value={imagePurpose}
            options={productImagePurposes}
            onChange={(value) => setImagePurpose(value)}
            disabled={isSubmitting}
          />

          <OptionGroup
            title="背景场景"
            value={sceneStyle}
            options={productSceneStyles}
            onChange={(value) => setSceneStyle(value)}
            disabled={isSubmitting}
          />

          <OptionGroup
            title="视觉风格"
            value={visualTone}
            options={productVisualTones}
            onChange={(value) => setVisualTone(value)}
            disabled={isSubmitting}
          />

          <label className="mt-5 block text-sm font-semibold text-zinc-900">
            促销文案
            <input
              value={promotionText}
              onChange={(event) => setPromotionText(event.target.value)}
              placeholder="例如：限时立减 20 元、买一送一"
              disabled={isSubmitting}
              className="mt-2 w-full rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>

          <div className="mt-5 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
            当前策略：{selectedPlatform?.label} · {selectedPurpose?.label}
          </div>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm xl:row-span-2">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-zinc-900 text-white">
              <ImageIcon aria-hidden="true" className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-zinc-950">生成结果</h2>
              <p className="text-sm leading-6 text-zinc-500">
                商品细节优先保真，场景按策略生成。
              </p>
            </div>
          </div>

          <div className="mt-5 grid min-h-[32rem] place-items-center rounded-lg bg-zinc-950 p-4 text-white">
            {result ? (
              <div className="w-full">
                <Image
                  unoptimized
                  src={result.src}
                  alt="电商商品图生成结果"
                  width={previewDimensions.width}
                  height={previewDimensions.height}
                  className="mx-auto h-auto max-h-[30rem] w-auto max-w-full rounded-md object-contain"
                />
                {result.revisedPrompt && (
                  <p className="mt-4 break-words text-sm leading-6 text-zinc-300 [overflow-wrap:anywhere]">
                    {result.revisedPrompt}
                  </p>
                )}
              </div>
            ) : (
              <div className="max-w-sm text-center">
                <Boxes aria-hidden="true" className="mx-auto h-10 w-10 text-zinc-400" />
                <p className="mt-4 text-xl font-semibold">等待生成商品图</p>
                <p className="mt-3 text-sm leading-6 text-zinc-400">
                  上传商品原图并完成策略配置后，结果会显示在这里。
                </p>
              </div>
            )}
          </div>

          {error && (
            <div className="mt-5 flex gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
              <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
              <p className="min-w-0 break-words [overflow-wrap:anywhere]">
                {error}
              </p>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-5 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-zinc-950 px-5 py-3 text-base font-semibold text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-500"
          >
            {isSubmitting ? (
              <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
            ) : (
              <Sparkles aria-hidden="true" className="h-5 w-5" />
            )}
            {isSubmitting ? "生成中" : "生成电商商品图"}
          </button>
        </section>

        <section className="rounded-lg border border-zinc-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-zinc-950">保真和限制</h2>
          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            必须保留
            <textarea
              value={preserveRequirements}
              onChange={(event) => setPreserveRequirements(event.target.value)}
              rows={3}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            禁止出现
            <textarea
              value={avoidElements}
              onChange={(event) => setAvoidElements(event.target.value)}
              rows={3}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>
          <label className="mt-4 block text-sm font-semibold text-zinc-900">
            补充说明
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="例如：商品放右侧，左侧留出卖点文字空间"
              rows={3}
              disabled={isSubmitting}
              className="mt-2 w-full resize-none rounded-md border border-zinc-300 bg-white px-3 py-2.5 text-sm leading-6 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:bg-zinc-100"
            />
          </label>
        </section>
      </form>
    </div>
  );
}

function OptionGroup<TId extends string>({
  title,
  value,
  options,
  onChange,
  disabled,
}: {
  title: string;
  value: TId;
  options: Array<{ id: TId; label: string; description: string }>;
  onChange: (value: TId) => void;
  disabled: boolean;
}) {
  return (
    <fieldset className="mt-5">
      <legend className="text-sm font-semibold text-zinc-900">{title}</legend>
      <div className="mt-3 grid gap-2">
        {options.map((option) => {
          const isSelected = option.id === value;

          return (
            <button
              key={option.id}
              type="button"
              disabled={disabled}
              onClick={() => onChange(option.id)}
              className={classNames(
                "rounded-md border px-3 py-2.5 text-left transition disabled:cursor-not-allowed disabled:opacity-60",
                isSelected
                  ? "border-zinc-950 bg-zinc-950 text-white"
                  : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-950",
              )}
            >
              <span className="block text-sm font-semibold">{option.label}</span>
              <span
                className={classNames(
                  "mt-1 block text-xs leading-5",
                  isSelected ? "text-zinc-300" : "text-zinc-500",
                )}
              >
                {option.description}
              </span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
```

- [ ] **Step 2: Route product tool to the dedicated workbench**

In `frontend/src/app/tools/[toolId]/page.tsx`, add:

```ts
import { ProductWorkbench } from "@/components/product-workbench";
```

Replace:

```tsx
      <section className="py-8">
        <ToolForm tool={tool} />
      </section>
```

with:

```tsx
      <section className="py-8">
        {tool.id === "product" ? (
          <ProductWorkbench tool={tool} />
        ) : (
          <ToolForm tool={tool} />
        )}
      </section>
```

- [ ] **Step 3: Run frontend lint**

Run:

```bash
rtk npm run lint --prefix frontend
```

Expected: PASS.

- [ ] **Step 4: Run frontend production build**

Run:

```bash
rtk npm run build --prefix frontend
```

Expected: PASS.

- [ ] **Step 5: Commit product workbench**

Run:

```bash
rtk git add frontend/src/components/product-workbench.tsx frontend/src/app/tools/[toolId]/page.tsx
rtk git commit -m "feat: add product image workbench"
```

Expected: commit succeeds.

---

### Task 6: Homepage and Visual Redesign

**Files:**
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/components/tool-card.tsx`
- Modify: `frontend/src/app/globals.css`
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Update app metadata**

In `frontend/src/app/layout.tsx`, change metadata to:

```ts
export const metadata: Metadata = {
  title: "电商商品图工作台",
  description:
    "按平台、用途、卖点和场景生成电商商品图的 AI 图片工作台。",
};
```

- [ ] **Step 2: Refresh global visual foundation**

Replace `frontend/src/app/globals.css` with:

```css
@import "tailwindcss";

:root {
  color-scheme: light;
  --ink: #18181b;
  --muted: #71717a;
  --paper: #f4f5f0;
  --panel: #ffffff;
  --line: #d7d9cf;
  --accent: #e0452f;
  --accent-ink: #7f1d1d;
  --gold: #b7791f;
  --teal: #0f766e;
  --blue: #2563eb;
}

* {
  box-sizing: border-box;
}

html {
  min-height: 100%;
  background:
    linear-gradient(90deg, rgba(24, 24, 27, 0.035) 1px, transparent 1px),
    linear-gradient(rgba(24, 24, 27, 0.035) 1px, transparent 1px),
    var(--paper);
  background-size: 28px 28px;
}

body {
  min-height: 100vh;
  margin: 0;
  color: var(--ink);
  font-family:
    "Microsoft YaHei",
    "PingFang SC",
    "Noto Sans CJK SC",
    sans-serif;
}

button,
input,
textarea,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
}

::selection {
  color: white;
  background: var(--accent);
}
```

- [ ] **Step 3: Refresh supporting tool card**

Replace `frontend/src/components/tool-card.tsx` with:

```tsx
import Link from "next/link";
import { ArrowUpRight, PackageSearch, Sparkles, UserRound, Wand2 } from "lucide-react";
import type { ImageTool } from "@/lib/tools";

const iconMap = {
  sparkles: Sparkles,
  wand: Wand2,
  user: UserRound,
  package: PackageSearch,
};

const accentClasses = {
  teal: "border-teal-700/20 bg-teal-50 text-teal-900",
  red: "border-red-700/20 bg-red-50 text-red-900",
  blue: "border-blue-700/20 bg-blue-50 text-blue-900",
  gold: "border-amber-700/25 bg-amber-50 text-amber-950",
};

export function ToolCard({ tool }: { tool: ImageTool }) {
  const Icon = iconMap[tool.icon];

  return (
    <Link
      href={`/tools/${tool.id}`}
      className="group grid min-h-56 content-between rounded-lg border border-zinc-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-zinc-950 hover:shadow-lg"
    >
      <div>
        <div className="flex items-start justify-between gap-3">
          <div
            className={`inline-flex h-11 w-11 items-center justify-center rounded-md border ${accentClasses[tool.accent]}`}
          >
            <Icon aria-hidden="true" className="h-5 w-5" />
          </div>
          <ArrowUpRight
            aria-hidden="true"
            className="h-4 w-4 text-zinc-400 transition group-hover:text-zinc-950"
          />
        </div>
        <p className="mt-5 text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
          {tool.eyebrow}
        </p>
        <h2 className="mt-2 text-2xl font-semibold leading-tight text-zinc-950">
          {tool.title}
        </h2>
        <p className="mt-3 text-sm leading-6 text-zinc-600">{tool.description}</p>
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        {tool.examples.map((example) => (
          <span
            key={example}
            className="rounded border border-zinc-200 px-2 py-1 text-xs text-zinc-600"
          >
            {example}
          </span>
        ))}
      </div>
    </Link>
  );
}
```

- [ ] **Step 4: Redesign homepage around product workbench priority**

Replace `frontend/src/app/page.tsx` with:

```tsx
import Link from "next/link";
import {
  ArrowRight,
  BadgePercent,
  ImagePlus,
  Layers3,
  PackageSearch,
  Sparkles,
} from "lucide-react";
import { ToolCard } from "@/components/tool-card";
import {
  imageTools,
  productImagePurposes,
  productPlatformStyles,
} from "@/lib/tools";

export default function Home() {
  const productTool = imageTools.find((tool) => tool.id === "product");
  const supportingTools = imageTools.filter((tool) => tool.id !== "product");

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col gap-5 border-b border-zinc-300 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-600">
            <PackageSearch aria-hidden="true" className="h-3.5 w-3.5" />
            Ecommerce image studio
          </p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-tight text-zinc-950 sm:text-5xl lg:text-6xl">
            电商商品图工作台
          </h1>
        </div>
        <p className="max-w-xl text-base leading-7 text-zinc-600">
          从商品原图出发，按拼多多、淘宝天猫、京东、小红书、抖音电商等实际平台流程生成主图、白底图、场景图和促销图。
        </p>
      </header>

      {productTool && (
        <section className="grid gap-5 py-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)]">
          <Link
            href="/tools/product"
            className="group overflow-hidden rounded-lg border border-zinc-950 bg-zinc-950 text-white shadow-xl transition hover:-translate-y-0.5"
          >
            <div className="grid min-h-[25rem] gap-6 p-6 sm:p-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(18rem,0.65fr)]">
              <div className="flex flex-col justify-between gap-8">
                <div>
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-md bg-white text-zinc-950">
                    <ImagePlus aria-hidden="true" className="h-6 w-6" />
                  </div>
                  <p className="mt-6 text-sm font-semibold uppercase tracking-[0.16em] text-zinc-400">
                    {productTool.eyebrow}
                  </p>
                  <h2 className="mt-3 max-w-2xl text-4xl font-semibold leading-tight sm:text-5xl">
                    按真实平台流程生成商品图
                  </h2>
                  <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-300">
                    不再只写一句提示词。先选平台和用途，再补卖点、场景、促销和保真要求，让模型按运营目标工作。
                  </p>
                </div>
                <span className="inline-flex w-fit items-center gap-2 rounded-md bg-white px-4 py-2.5 text-sm font-semibold text-zinc-950 transition group-hover:bg-amber-200">
                  打开商品图工作台
                  <ArrowRight aria-hidden="true" className="h-4 w-4" />
                </span>
              </div>

              <div className="grid content-start gap-3">
                <PreviewPanel
                  icon={<BadgePercent aria-hidden="true" className="h-4 w-4" />}
                  title="平台风格"
                  items={productPlatformStyles.map((item) => item.label)}
                />
                <PreviewPanel
                  icon={<Layers3 aria-hidden="true" className="h-4 w-4" />}
                  title="图片用途"
                  items={productImagePurposes.map((item) => item.label)}
                />
                <div className="rounded-lg border border-white/15 bg-white/10 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <Sparkles aria-hidden="true" className="h-4 w-4" />
                    一次提交完整运营需求
                  </div>
                  <p className="mt-3 text-sm leading-6 text-zinc-300">
                    商品类目、核心卖点、促销文案、必须保留和禁止元素都会进入后端结构化 prompt。
                  </p>
                </div>
              </div>
            </div>
          </Link>

          <aside className="grid gap-4">
            {supportingTools.map((tool) => (
              <ToolCard key={tool.id} tool={tool} />
            ))}
          </aside>
        </section>
      )}
    </main>
  );
}

function PreviewPanel({
  icon,
  title,
  items,
}: {
  icon: React.ReactNode;
  title: string;
  items: string[];
}) {
  return (
    <div className="rounded-lg border border-white/15 bg-white/10 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-white">
        {icon}
        {title}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className="rounded border border-white/15 bg-white/10 px-2 py-1 text-xs text-zinc-200"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Add missing React type import if lint requires it**

If the lint step reports that `React` is undefined in `frontend/src/app/page.tsx`, add this import at the top:

```ts
import type { ReactNode } from "react";
```

Then change `React.ReactNode` to `ReactNode` in `PreviewPanel` props:

```ts
  icon: ReactNode;
```

- [ ] **Step 6: Run frontend lint and build**

Run:

```bash
rtk npm run lint --prefix frontend
```

Expected: PASS.

Run:

```bash
rtk npm run build --prefix frontend
```

Expected: PASS.

- [ ] **Step 7: Commit visual redesign**

Run:

```bash
rtk git add frontend/src/app/page.tsx frontend/src/components/tool-card.tsx frontend/src/app/globals.css frontend/src/app/layout.tsx
rtk git commit -m "feat: redesign ecommerce workbench homepage"
```

Expected: commit succeeds.

---

### Task 7: Final Verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Run all backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend lint**

Run:

```bash
rtk npm run lint --prefix frontend
```

Expected: PASS.

- [ ] **Step 3: Run frontend production build**

Run:

```bash
rtk npm run build --prefix frontend
```

Expected: PASS.

- [ ] **Step 4: Check worktree status**

Run:

```bash
rtk git status --short
```

Expected: no output.

- [ ] **Step 5: Manual smoke test with dev servers**

Start the backend in one terminal:

```bash
rtk backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --reload
```

Expected: backend serves `http://127.0.0.1:8000`.

Start the frontend in another terminal:

```bash
rtk npm run dev --prefix frontend
```

Expected: frontend serves `http://localhost:3000`.

Open these routes:

- `http://localhost:3000`
- `http://localhost:3000/tools/product`
- `http://localhost:3000/tools/creator`
- `http://localhost:3000/tools/restore`
- `http://localhost:3000/tools/avatar`

Expected:

- Homepage prioritizes the ecommerce product workbench.
- Product page shows structured platform, purpose, category, selling point, scene, tone, promotion, preservation, and avoidance controls.
- Other tool pages still show the generic form.
- Product submit without an uploaded image shows the existing missing image error.

---

## Self-Review

Spec coverage:

- Product-focused ecommerce workbench: Tasks 4, 5, and 6.
- Structured product fields: Tasks 2, 3, 4, and 5.
- Pinduoduo, Taobao/Tmall, JD, Xiaohongshu, Douyin styles: Tasks 1 and 4.
- Main image, white background, scene image, promotion image, detail hero: Tasks 1 and 4.
- Backend prompt composition: Tasks 2 and 3.
- Existing tools remain functional: Tasks 4, 5, 6, and 7.
- Verification: Task 7.

Placeholder scan:

- The plan contains concrete file paths, commands, expected results, test snippets, and implementation snippets.
- The plan does not leave unspecified product field names, option ids, route parameter names, or commit boundaries.

Type consistency:

- Backend uses snake_case fields internally: `platform_style`, `image_purpose`, `product_category`, `selling_points`, `scene_style`, `visual_tone`, `promotion_text`, `preserve_requirements`, `avoid_elements`.
- Frontend and route use camelCase `FormData` names: `platformStyle`, `imagePurpose`, `productCategory`, `sellingPoints`, `sceneStyle`, `visualTone`, `promotionText`, `preserveRequirements`, `avoidElements`.
- `ProductPlatformStyleId` and `ProductImagePurposeId` ids match between backend and frontend.

