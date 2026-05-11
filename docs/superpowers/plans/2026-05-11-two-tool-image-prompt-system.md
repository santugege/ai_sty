# Two Tool Image Prompt System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first version of a two-tool prompt system where ChatGPT general image conversation supports pure text-to-image and image editing, while product image generation keeps separate ecommerce-specific prompt logic.

**Architecture:** Add a focused prompt module that owns shared quality guidance plus separate ChatGPT and product prompt composition. Extend the agent planner and tool layer from `answer/edit` to `answer/generate/edit`, with separate image generation and image editing tools. Keep `/api/images/generate` as the product path and `/api/agent/sessions` as the ChatGPT conversation path.

**Tech Stack:** FastAPI, SQLAlchemy, OpenAI Python SDK, pytest, Next.js/React source-level tests.

---

## File Structure

- Create: `backend/app/image_prompts.py`
  - Owns `GLOBAL_IMAGE_QUALITY_PROMPT`, `CHATGPT_GENERAL_IMAGE_PROMPT`, `PRODUCT_IMAGE_PROMPT`, prompt boundary constants, `ChatGptImageBrief`, and prompt composition helpers.
- Modify: `backend/app/agent_openai.py`
  - Uses ChatGPT general prompt, accepts `generate`, validates structured tool instructions, and keeps product terms out of ChatGPT prompt.
- Modify: `backend/app/agent_tools.py`
  - Adds `ChatGptImageGenerateTool`, renames/generalizes the edit tool, supports structured prompt rendering, and sends `quality="high"`.
- Modify: `backend/app/agent_service.py`
  - Allows `generate` without current image, keeps `edit` requiring current image, and persists generated image versions.
- Modify: `backend/app/main.py`
  - Registers both ChatGPT image tools in `build_agent_service`.
- Modify: `backend/app/image_request.py`
  - Routes product prompt composition through `image_prompts.py`.
- Modify: `backend/app/openai_images.py`
  - Sends `quality="high"` for product image calls.
- Test: `backend/tests/test_image_prompts.py`
  - Prompt boundary tests.
- Modify: `backend/tests/test_agent_openai.py`
  - Planner generate/edit validation tests.
- Modify: `backend/tests/test_agent_tools.py`
  - Generate/edit tool API call tests.
- Modify: `backend/tests/test_agent_service.py`
  - ChatGPT text-to-image and edit-without-image behavior tests.
- Modify: `backend/tests/test_image_request.py`
  - Product prompt composition still contains ecommerce rules.
- Modify: `backend/tests/test_openai_images.py`
  - Product image calls use high quality.
- Optional modify: `frontend/tests/agent-workbench.test.mjs`
  - Only if source-level tests currently assert edit-only behavior.

---

### Task 1: Add Prompt Module With Boundary Tests

**Files:**
- Create: `backend/app/image_prompts.py`
- Create: `backend/tests/test_image_prompts.py`

- [ ] **Step 1: Write prompt boundary tests**

Create `backend/tests/test_image_prompts.py`:

```python
from app.image_prompts import (
    CHATGPT_GENERAL_IMAGE_PROMPT,
    PRODUCT_IMAGE_PROMPT,
    ChatGptImageBrief,
    compose_chatgpt_tool_instruction,
    compose_product_image_prompt,
)
from app.image_request import ProductGenerationSettings, ProductImageFields
from app.tools import get_tool_by_id


def test_chatgpt_general_prompt_has_no_ecommerce_assumptions():
    forbidden_terms = [
        "ecommerce",
        "product listing",
        "marketplace",
        "platform style",
        "selling point",
        "Pinduoduo",
        "Taobao",
        "Tmall",
        "JD",
        "Xiaohongshu",
        "Douyin",
        "商品",
        "平台",
        "卖点",
        "主图",
    ]

    for term in forbidden_terms:
        assert term.lower() not in CHATGPT_GENERAL_IMAGE_PROMPT.lower()


def test_product_prompt_contains_ecommerce_preservation_rules():
    assert "product" in PRODUCT_IMAGE_PROMPT.lower()
    assert "logo" in PRODUCT_IMAGE_PROMPT.lower()
    assert "visible text" in PRODUCT_IMAGE_PROMPT.lower()
    assert "commercial" in PRODUCT_IMAGE_PROMPT.lower()


def test_compose_chatgpt_tool_instruction_renders_structured_brief():
    prompt = compose_chatgpt_tool_instruction(
        ChatGptImageBrief(
            user_goal="Create a cinematic city street at night.",
            scene="Rainy city street",
            subject="A person holding a transparent umbrella",
            style="Photorealistic",
            composition="Wide shot with the subject centered",
            lighting="Neon reflections on wet pavement",
            preserve=[],
            change=[],
            avoid=["watermark", "unreadable text"],
        )
    )

    assert "User goal: Create a cinematic city street at night." in prompt
    assert "Style: Photorealistic" in prompt
    assert "Avoid:" in prompt
    assert "- watermark" in prompt


def test_compose_product_image_prompt_keeps_product_fields():
    tool = get_tool_by_id("product")
    prompt = compose_product_image_prompt(
        tool=tool,
        user_prompt="Keep the bottle centered.",
        product_fields=ProductImageFields(
            platform_style="pinduoduo",
            image_purpose="main-image",
            product_category="drink",
            selling_points="fresh taste",
            scene_style="bright studio",
            visual_tone="clean",
            promotion_text="",
            preserve_requirements="preserve label",
            avoid_elements="extra bottles",
        ),
        generation_settings=ProductGenerationSettings(
            aspect_ratio="1:1",
            image_count=1,
        ),
    )

    assert "Product preservation rules:" in prompt
    assert "Platform style" in prompt
    assert "Image purpose" in prompt
    assert "Selling points: fresh taste" in prompt
    assert "Preserve requirements: preserve label" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_image_prompts.py -q
```

Expected: FAIL because `app.image_prompts` does not exist.

- [ ] **Step 3: Add prompt module**

Create `backend/app/image_prompts.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from app.tools import (
    ImageTool,
    get_product_image_purpose,
    get_product_platform_style,
)


GLOBAL_IMAGE_QUALITY_PROMPT = (
    "Global image quality rules:\n"
    "- Follow the user's explicit intent.\n"
    "- Keep the main subject clear, coherent, and visually stable.\n"
    "- Use believable composition, lighting, perspective, texture, and material detail.\n"
    "- Avoid low-resolution artifacts, warped anatomy, distorted objects, unintended watermarks, unintended extra text, and illegible text.\n"
    "- For edits, preserve every region and visual detail the user did not ask to change.\n"
    "- When literal text is requested, keep it short, quote it exactly, and prioritize legibility."
)


CHATGPT_GENERAL_IMAGE_PROMPT = (
    "You are a general ChatGPT-style image assistant.\n"
    "You can create new images from text and edit user-provided or current conversation images.\n"
    "Understand natural language, conversation history, reference image roles, and the user's visual intent.\n"
    "For new images, write a precise creative brief with subject, scene, style, composition, lighting, mood, and avoid constraints.\n"
    "For edits, state exactly what should change and what must stay the same.\n"
    "Ask a concise clarification question when the visual request is too ambiguous to produce a good result.\n"
    "Do not invent commercial constraints unless the user explicitly asks for them."
)


PRODUCT_IMAGE_PROMPT = (
    "You are an ecommerce product image generation assistant.\n"
    "Generate commercially usable product visuals from the uploaded product image.\n"
    "Preserve the product shape, color, logo, package structure, visible text, material cues, and identifying details.\n"
    "Do not invent extra accessories, fake labels, misleading claims, or features not visible or described by the user.\n"
    "Keep the product visually accurate while adapting scene, composition, platform style, image purpose, and user brief."
)


@dataclass(frozen=True)
class ChatGptImageBrief:
    user_goal: str = ""
    scene: str = ""
    subject: str = ""
    style: str = ""
    composition: str = ""
    lighting: str = ""
    preserve: list[str] = field(default_factory=list)
    change: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)


def compose_chatgpt_planner_system_prompt() -> str:
    return "\n\n".join(
        [
            GLOBAL_IMAGE_QUALITY_PROMPT,
            CHATGPT_GENERAL_IMAGE_PROMPT,
            (
                "Return JSON only. Valid actions are answer, generate, and edit. "
                "Use action generate with tool_name chatgpt_image_generate when the user wants a new image from text. "
                "Use action edit with tool_name chatgpt_image_edit when the user wants to change an uploaded or current image. "
                "Use action answer for clarifying questions, confirmations, or text-only help. "
                "For generate and edit, tool_instruction must be an object with user_goal, scene, subject, style, composition, lighting, preserve, change, and avoid."
            ),
        ]
    )


def compose_chatgpt_tool_instruction(brief: ChatGptImageBrief) -> str:
    sections = [
        "Create or edit the image using this structured brief.",
        _line("User goal", brief.user_goal),
        _line("Scene", brief.scene),
        _line("Subject", brief.subject),
        _line("Style", brief.style),
        _line("Composition", brief.composition),
        _line("Lighting", brief.lighting),
        _list("Preserve", brief.preserve),
        _list("Change", brief.change),
        _list("Avoid", brief.avoid),
    ]
    return "\n".join(section for section in sections if section)


def compose_product_image_prompt(
    *,
    tool: ImageTool,
    user_prompt: str,
    product_fields,
    generation_settings,
) -> str:
    platform_rule = get_product_platform_style(product_fields.platform_style)
    purpose_rule = get_product_image_purpose(product_fields.image_purpose)
    if platform_rule is None:
        raise ValueError("Invalid product platform style.")
    if purpose_rule is None:
        raise ValueError("Invalid product image purpose.")

    sections = [
        GLOBAL_IMAGE_QUALITY_PROMPT,
        PRODUCT_IMAGE_PROMPT,
        tool.base_prompt,
        (
            "Product preservation rules:\n"
            "- Preserve the uploaded product's shape, color, logo, package structure, visible text, material cues, and identifying details.\n"
            "- Do not invent extra accessories, fake labels, misleading claims, or features not visible or described by the user.\n"
            "- Keep the product commercially usable and avoid visual deformation."
        ),
        f"Platform style ({platform_rule.label}):\n{platform_rule.prompt}",
        f"Image purpose ({purpose_rule.label}):\n{purpose_rule.prompt}",
    ]
    brief_lines = _product_brief_lines(product_fields, user_prompt, generation_settings)
    if brief_lines:
        sections.append("User product brief:\n" + "\n".join(brief_lines))
    return "\n\n".join(sections)


def _product_brief_lines(product_fields, user_prompt: str, generation_settings) -> list[str]:
    field_lines = [
        ("Aspect ratio", getattr(generation_settings, "aspect_ratio", "")),
        ("Image count", str(getattr(generation_settings, "image_count", ""))),
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


def _line(label: str, value: str) -> str:
    return f"{label}: {value.strip()}" if value.strip() else ""


def _list(label: str, values: list[str]) -> str:
    normalized = [value.strip() for value in values if value.strip()]
    if not normalized:
        return ""
    return label + ":\n" + "\n".join(f"- {value}" for value in normalized)
```

- [ ] **Step 4: Run prompt tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_image_prompts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/image_prompts.py backend/tests/test_image_prompts.py
rtk git commit -m "feat: add image prompt boundaries"
```

---

### Task 2: Route Product Prompt Composition Through Prompt Module

**Files:**
- Modify: `backend/app/image_request.py`
- Modify: `backend/tests/test_image_request.py`

- [ ] **Step 1: Add product prompt regression test**

Append to `backend/tests/test_image_request.py`:

```python
def test_product_prompt_uses_shared_quality_and_product_layers():
    tool = get_tool_by_id("product")
    prompt = compose_tool_prompt(
        tool,
        "保留瓶身居中",
        ProductImageFields(
            platform_style="pinduoduo",
            image_purpose="main-image",
            product_category="饮料",
            selling_points="清爽",
            scene_style="明亮棚拍",
            visual_tone="干净",
            promotion_text="",
            preserve_requirements="保留瓶身标签",
            avoid_elements="不要额外瓶子",
        ),
        ProductGenerationSettings(aspect_ratio="1:1", image_count=1),
    )

    assert "Global image quality rules:" in prompt
    assert "Product preservation rules:" in prompt
    assert "Platform style" in prompt
    assert "Image purpose" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_image_request.py::test_product_prompt_uses_shared_quality_and_product_layers -q
```

Expected: FAIL because existing product prompt does not include the new global quality layer.

- [ ] **Step 3: Update product prompt composition**

In `backend/app/image_request.py`, add this import:

```python
from app.image_prompts import compose_product_image_prompt
```

Replace the body of `compose_product_prompt` with:

```python
def compose_product_prompt(
    tool: ImageTool,
    user_prompt: str,
    product_fields: ProductImageFields,
    generation_settings: ProductGenerationSettings | None = None,
) -> str:
    platform_rule = get_product_platform_style(product_fields.platform_style)
    purpose_rule = get_product_image_purpose(product_fields.image_purpose)

    if platform_rule is None:
        raise ImageRequestError(400, "请选择有效的平台风格。")

    if purpose_rule is None:
        raise ImageRequestError(400, "请选择有效的图片用途。")

    try:
        return compose_product_image_prompt(
            tool=tool,
            user_prompt=user_prompt,
            product_fields=product_fields,
            generation_settings=generation_settings or ProductGenerationSettings(),
        )
    except ValueError as error:
        raise ImageRequestError(400, str(error)) from error
```

Keep `build_product_brief_lines` in place for now only if other tests import it directly; otherwise delete it in a later cleanup.

- [ ] **Step 4: Run image request tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_image_request.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/image_request.py backend/tests/test_image_request.py
rtk git commit -m "refactor: route product prompts through prompt module"
```

---

### Task 3: Extend Planner To Support Generate And Structured Briefs

**Files:**
- Modify: `backend/app/agent_openai.py`
- Modify: `backend/tests/test_agent_openai.py`

- [ ] **Step 1: Add planner generate tests**

Append to `backend/tests/test_agent_openai.py`:

```python
def test_request_conversation_turn_accepts_generate_action():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                id="resp_generate",
                output_text=(
                    '{"action":"generate","assistant_message":"I will create it.",'
                    '"tool_name":"chatgpt_image_generate",'
                    '"tool_instruction":{'
                    '"user_goal":"Create a calm mountain lake.",'
                    '"scene":"Mountain lake at sunrise",'
                    '"subject":"A still lake",'
                    '"style":"Photorealistic",'
                    '"composition":"Wide landscape",'
                    '"lighting":"Soft sunrise",'
                    '"preserve":[],'
                    '"change":[],'
                    '"avoid":["watermark"]'
                    "}}"
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    decision = request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="生成一张日出湖面",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    assert decision.action == "generate"
    assert decision.tool_name == "chatgpt_image_generate"
    assert "Mountain lake at sunrise" in decision.tool_instruction


def test_request_conversation_turn_uses_chatgpt_general_prompt_without_product_terms():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="resp_answer",
                output_text=(
                    '{"action":"answer","assistant_message":"Please upload an image.",'
                    '"tool_name":null,"tool_instruction":null}'
                ),
            )

    class FakeClient:
        def __init__(self, api_key):
            self.responses = FakeResponses()

    request_conversation_turn(
        api_key="key",
        agent_model="gpt-5.5",
        user_message="帮我改图",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        client_factory=FakeClient,
    )

    system_prompt = calls[0]["input"][0]["content"]
    assert "general ChatGPT-style image assistant" in system_prompt
    assert "Pinduoduo" not in system_prompt
    assert "Taobao" not in system_prompt
    assert "selling point" not in system_prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_openai.py::test_request_conversation_turn_accepts_generate_action backend/tests/test_agent_openai.py::test_request_conversation_turn_uses_chatgpt_general_prompt_without_product_terms -q
```

Expected: FAIL because `generate` is not a valid action and the system prompt is still inline.

- [ ] **Step 3: Update planner dataclass and prompt**

In `backend/app/agent_openai.py`, add:

```python
from app.image_prompts import (
    ChatGptImageBrief,
    compose_chatgpt_planner_system_prompt,
    compose_chatgpt_tool_instruction,
)
```

Update the dataclass action type:

```python
class ConversationTurnDecision:
    action: Literal["answer", "generate", "edit"]
    assistant_message: str
    tool_name: str | None
    tool_instruction: str | None
    response_id: str | None
```

Replace the inline system prompt in `request_conversation_turn` with:

```python
"content": compose_chatgpt_planner_system_prompt(),
```

Update action validation:

```python
if action not in {"answer", "edit", "generate", "clarify"}:
    raise RuntimeError("Agent decision action was invalid.")
```

Update edit validation and add generate validation:

```python
if normalized_action == "generate" and tool_name != "chatgpt_image_generate":
    raise RuntimeError("Agent generate decision was invalid.")
if normalized_action == "edit" and tool_name != "chatgpt_image_edit":
    raise RuntimeError("Agent edit decision was invalid.")
if normalized_action in {"generate", "edit"}:
    if tool_instruction is None:
        raise RuntimeError("Agent image decision was invalid.")
    rendered_instruction = _render_tool_instruction(tool_instruction)
else:
    rendered_instruction = tool_instruction
```

Return `tool_instruction=rendered_instruction`.

Add this helper:

```python
def _render_tool_instruction(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            raise RuntimeError("Agent image decision was invalid.")
        return value
    if not isinstance(value, dict):
        raise RuntimeError("Agent image decision was invalid.")
    brief = ChatGptImageBrief(
        user_goal=str(value.get("user_goal") or ""),
        scene=str(value.get("scene") or ""),
        subject=str(value.get("subject") or ""),
        style=str(value.get("style") or ""),
        composition=str(value.get("composition") or ""),
        lighting=str(value.get("lighting") or ""),
        preserve=_string_list(value.get("preserve")),
        change=_string_list(value.get("change")),
        avoid=_string_list(value.get("avoid")),
    )
    rendered = compose_chatgpt_tool_instruction(brief)
    if not rendered.strip():
        raise RuntimeError("Agent image decision was invalid.")
    return rendered


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
```

- [ ] **Step 4: Update existing tests for new edit tool name**

In `backend/tests/test_agent_openai.py`, replace expected edit tool names:

```python
"gpt_image_2_edit"
```

with:

```python
"chatgpt_image_edit"
```

Also update assertions that expect `tool_name == "gpt_image_2_edit"` to `chatgpt_image_edit`.

- [ ] **Step 5: Run planner tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_openai.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
rtk git add backend/app/agent_openai.py backend/tests/test_agent_openai.py
rtk git commit -m "feat: support chatgpt image generate decisions"
```

---

### Task 4: Add ChatGPT Generate And Edit Image Tools

**Files:**
- Modify: `backend/app/agent_tools.py`
- Modify: `backend/tests/test_agent_tools.py`

- [ ] **Step 1: Add tool tests**

Append to `backend/tests/test_agent_tools.py`:

```python
def test_create_openai_image_client_generates_image_with_high_quality():
    class FakeImages:
        def __init__(self):
            self.generate_kwargs = None

        def generate(self, **kwargs):
            self.generate_kwargs = kwargs
            return {"data": [{"b64_json": "Z2VuZXJhdGVk"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    result = image_client.generate("Create a mountain lake.", "1536x1024")

    assert result == b"generated"
    assert fake_client.images.generate_kwargs["model"] == "gpt-image-2"
    assert fake_client.images.generate_kwargs["prompt"] == "Create a mountain lake."
    assert fake_client.images.generate_kwargs["size"] == "1536x1024"
    assert fake_client.images.generate_kwargs["quality"] == "high"


def test_create_openai_image_client_edits_image_with_high_quality():
    class FakeImages:
        def __init__(self):
            self.edit_kwargs = None

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "ZWRpdGVk"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    result = image_client.edit(
        AgentToolContext(
            image_bytes=b"original",
            image_name="current.png",
            mime_type="image/png",
            instruction="Make the sky warmer.",
            size="1536x1024",
        )
    )

    assert result == b"edited"
    assert fake_client.images.edit_kwargs["quality"] == "high"
    assert fake_client.images.edit_kwargs["prompt"] == "Make the sky warmer."
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_tools.py::test_create_openai_image_client_generates_image_with_high_quality backend/tests/test_agent_tools.py::test_create_openai_image_client_edits_image_with_high_quality -q
```

Expected: FAIL because the image client is currently a function and edit quality is `auto`.

- [ ] **Step 3: Refactor image client wrapper**

In `backend/app/agent_tools.py`, add:

```python
@dataclass(frozen=True)
class OpenAIImageClient:
    api_key: str
    image_model: str
    base_url: str | None = None
    client_factory: Callable[..., Any] = OpenAI

    def generate(self, instruction: str, size: str) -> bytes:
        client = self.client_factory(**openai_client_kwargs(self.api_key, self.base_url))
        response = client.images.generate(
            model=self.image_model,
            prompt=instruction,
            size=size,
            quality="high",
        )
        return _decode_first_image(response)

    def edit(self, context: AgentToolContext) -> bytes:
        client = self.client_factory(**openai_client_kwargs(self.api_key, self.base_url))
        image_file = BytesIO(context.image_bytes)
        image_file.name = context.image_name
        response = client.images.edit(
            model=self.image_model,
            image=image_file,
            prompt=context.instruction,
            size=context.size,
            quality="high",
        )
        return _decode_first_image(response)
```

Update `create_openai_image_client` to return `OpenAIImageClient`:

```python
def create_openai_image_client(
    api_key: str,
    image_model: str,
    base_url: str | None = None,
    client_factory: Callable[..., Any] = OpenAI,
) -> OpenAIImageClient:
    return OpenAIImageClient(
        api_key=api_key,
        image_model=image_model,
        base_url=base_url,
        client_factory=client_factory,
    )
```

Move the response decode logic into:

```python
def _decode_first_image(response: Any) -> bytes:
    data = _read(response, "data") or []
    first_image = data[0] if data else None
    b64_json = _read(first_image, "b64_json") if first_image is not None else None
    if not b64_json:
        raise RuntimeError("OpenAI did not return image data.")
    try:
        return base64.b64decode(b64_json, validate=True)
    except (binascii.Error, ValueError) as error:
        raise RuntimeError("OpenAI returned invalid base64 image data.") from error
```

- [ ] **Step 4: Add separate generate/edit tools**

Replace `GptImage2EditTool` with compatibility alias plus new tools:

```python
class ChatGptImageGenerateTool:
    name = "chatgpt_image_generate"
    description = "Generate a new image from a ChatGPT general image prompt."

    def __init__(self, image_client: OpenAIImageClient, image_model: str | None = None):
        self._image_client = image_client
        self.image_model = image_model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        image_bytes = self._image_client.generate(context.instruction, context.size)
        return AgentToolResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt=None,
            model=self.image_model,
        )


class ChatGptImageEditTool:
    name = "chatgpt_image_edit"
    description = "Edit the current image using a ChatGPT general image prompt."

    def __init__(self, image_client: OpenAIImageClient, image_model: str | None = None):
        self._image_client = image_client
        self.image_model = image_model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        image_bytes = self._image_client.edit(context)
        return AgentToolResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt=None,
            model=self.image_model,
        )


GptImage2EditTool = ChatGptImageEditTool
```

- [ ] **Step 5: Update existing tests for wrapper object**

In existing `backend/tests/test_agent_tools.py`, update direct calls:

```python
image_client(context)
```

to:

```python
image_client.edit(context)
```

Update assertions expecting `quality == "auto"` to `quality == "high"`.

- [ ] **Step 6: Run tool tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_tools.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add backend/app/agent_tools.py backend/tests/test_agent_tools.py
rtk git commit -m "feat: split chatgpt image generate and edit tools"
```

---

### Task 5: Let Agent Service Generate Without Current Image

**Files:**
- Modify: `backend/app/agent_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_agent_service.py`
- Modify: `backend/tests/test_agent_routes.py`

- [ ] **Step 1: Add service tests for generate and edit guard**

Append to `backend/tests/test_agent_service.py`:

```python
def test_chatgpt_service_generates_image_without_current_image(agent_repo, fake_storage):
    class FakeTool:
        name = "chatgpt_image_generate"
        description = "Generate"

        def execute(self, context):
            assert context.image_bytes == b""
            assert context.instruction == "Create a mountain lake."
            return AgentToolResult(
                image_bytes=b"generated",
                mime_type="image/png",
                prompt=context.instruction,
                revised_prompt=None,
                model="gpt-image-2",
            )

    service = ChatGptConversationService(
        planner=lambda **kwargs: ConversationTurnDecision(
            action="generate",
            assistant_message="I created it.",
            tool_name="chatgpt_image_generate",
            tool_instruction="Create a mountain lake.",
            response_id="resp_generate",
        ),
        tools={"chatgpt_image_generate": FakeTool()},
        repo=agent_repo,
        storage=fake_storage,
    )

    envelope = service.create_session(
        message="生成一张山间湖面",
        attachments=[],
        size="1536x1024",
    )

    assistant_messages = [
        message for message in envelope.messages if message.role == "assistant"
    ]
    assert assistant_messages[-1].image is not None
    assert assistant_messages[-1].image.model == "gpt-image-2"


def test_chatgpt_service_rejects_edit_without_current_image(agent_repo, fake_storage):
    service = ChatGptConversationService(
        planner=lambda **kwargs: ConversationTurnDecision(
            action="edit",
            assistant_message="Please upload an image.",
            tool_name="chatgpt_image_edit",
            tool_instruction="Make it brighter.",
            response_id="resp_edit",
        ),
        tools={},
        repo=agent_repo,
        storage=fake_storage,
    )

    with pytest.raises(ConversationInputError, match="Please upload an image first."):
        service.create_session(
            message="把这张图调亮",
            attachments=[],
            size="1536x1024",
        )
```

If fixture names differ in the file, adapt only the fixture parameters to the existing names and keep the behavior identical.

- [ ] **Step 2: Run tests to verify generate fails**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_service.py::test_chatgpt_service_generates_image_without_current_image backend/tests/test_agent_service.py::test_chatgpt_service_rejects_edit_without_current_image -q
```

Expected: FAIL because service only handles answer/edit and requires a current image before tool execution.

- [ ] **Step 3: Register both tools in main**

In `backend/app/main.py`, update imports:

```python
from app.agent_tools import (
    ChatGptImageEditTool,
    ChatGptImageGenerateTool,
    create_openai_image_client,
)
```

Update `tools` in `build_agent_service`:

```python
tools={
    "chatgpt_image_generate": ChatGptImageGenerateTool(
        image_client=image_client,
        image_model=image_model,
    ),
    "chatgpt_image_edit": ChatGptImageEditTool(
        image_client=image_client,
        image_model=image_model,
    ),
},
```

- [ ] **Step 4: Update service action handling**

In `backend/app/agent_service.py`, after the `answer` branch and before the edit current-image guard, add a `generate` branch:

```python
if decision.action == "generate":
    tool = self.tools.get(decision.tool_name or "")
    if tool is None:
        raise AgentServiceError("The selected agent tool is not available.")
    result = self._execute_image_tool(
        tool,
        decision,
        _PersistentImageSource(
            image_bytes=b"",
            mime_type="image/png",
            name="generated-image.png",
        ),
        size,
    )
    stored = self.storage.write_image(
        result.image_bytes,
        mime_type=result.mime_type,
        prefix=f"agent-sessions/{parsed_session_id}",
    )
    persisted_storage_keys.append(stored.storage_key)
    generated_version = self.repo.add_image_version(
        session_id=parsed_session_id,
        parent_version_id=(current_version.id if current_version is not None else None),
        storage_key=stored.storage_key,
        mime_type=stored.mime_type,
        prompt=result.prompt,
        model=result.model,
        revised_prompt=result.revised_prompt,
        public_url=getattr(stored, "public_url", None),
    )
    persisted_version_ids.append(generated_version.id)
    self.repo.set_current_version(parsed_session_id, generated_version.id)
    assistant_message = self.repo.add_message(
        parsed_session_id,
        role="assistant",
        content=decision.assistant_message,
        response_id=decision.response_id,
        image_version_id=generated_version.id,
    )
    persisted_message_ids.append(assistant_message.id)
    self._ensure_message_after(assistant_message, user_message)
    self.repo.set_previous_response_id(parsed_session_id, decision.response_id)
    self._maybe_refresh_summary(parsed_session_id)
    return self.get_session(parsed_session_id)
```

Keep the existing `if current_version is None: raise ConversationInputError("Please upload an image first.")` for `edit`.

- [ ] **Step 5: Update old tool names in service tests**

Search in `backend/tests/test_agent_service.py` and `backend/tests/test_agent_routes.py` for:

```text
gpt_image_2_edit
```

Replace with:

```text
chatgpt_image_edit
```

- [ ] **Step 6: Run agent service and route tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_service.py backend/tests/test_agent_routes.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
rtk git add backend/app/agent_service.py backend/app/main.py backend/tests/test_agent_service.py backend/tests/test_agent_routes.py
rtk git commit -m "feat: allow chatgpt text to image generation"
```

---

### Task 6: Use High Quality For Product Image Calls

**Files:**
- Modify: `backend/app/openai_images.py`
- Modify: `backend/tests/test_openai_images.py`

- [ ] **Step 1: Add product quality tests**

In `backend/tests/test_openai_images.py`, update existing assertions for image API kwargs or add:

```python
def test_product_image_generate_uses_high_quality():
    class FakeImages:
        def __init__(self):
            self.generate_kwargs = None
            self.edit_kwargs = None

        def generate(self, **kwargs):
            self.generate_kwargs = kwargs
            return {"data": [{"b64_json": "abc123"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("product"),
            prompt="生成干净背景",
            size="1024x1024",
            generation_settings=ProductGenerationSettings(),
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert fake_client.images.generate_kwargs["quality"] == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_openai_images.py::test_product_image_generate_uses_high_quality -q
```

Expected: FAIL because product calls use `quality="auto"`.

- [ ] **Step 3: Update product image API quality**

In `backend/app/openai_images.py`, change both `quality="auto"` arguments to:

```python
quality="high",
```

- [ ] **Step 4: Run image API tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_openai_images.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
rtk git add backend/app/openai_images.py backend/tests/test_openai_images.py
rtk git commit -m "feat: use high quality image output"
```

---

### Task 7: Frontend Source Test Sweep

**Files:**
- Optional modify: `frontend/tests/agent-workbench.test.mjs`
- Optional modify: `frontend/src/components/agent-image-workbench.tsx`

- [ ] **Step 1: Run frontend tests**

Run:

```bash
cd frontend
rtk npm test
```

Expected: PASS or failures only where tests assert edit-only ChatGPT behavior.

- [ ] **Step 2: Update source-level tests only if needed**

If `frontend/tests/agent-workbench.test.mjs` expects uploaded images for every agent generation, change that assertion to allow text-only messages. The existing UI already permits text-only submit through:

```typescript
const canSubmit =
  !isSubmitting && (message.trim().length > 0 || selectedImages.length > 0);
```

Do not add product fields to `frontend/src/components/agent-image-workbench.tsx`.

- [ ] **Step 3: Run frontend lint**

Run:

```bash
cd frontend
rtk npm run lint
```

Expected: PASS.

- [ ] **Step 4: Commit if frontend changed**

If frontend files changed:

```bash
rtk git add frontend/tests/agent-workbench.test.mjs frontend/src/components/agent-image-workbench.tsx
rtk git commit -m "test: keep chatgpt image workbench generic"
```

If no frontend files changed, skip commit.

---

### Task 8: Final Verification

**Files:**
- No code changes unless a verification failure reveals a missed required update.

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_image_prompts.py backend/tests/test_agent_openai.py backend/tests/test_agent_tools.py backend/tests/test_agent_service.py backend/tests/test_agent_routes.py backend/tests/test_image_request.py backend/tests/test_openai_images.py -q
```

Expected: PASS.

- [ ] **Step 2: Run broader backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_routes.py backend/tests/test_auth_routes.py backend/tests/test_agent_service.py backend/tests/test_agent_tools.py backend/tests/test_agent_openai.py backend/tests/test_main.py backend/tests/test_image_request.py backend/tests/test_openai_images.py -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend tests and lint**

Run:

```bash
cd frontend
rtk npm test
rtk npm run lint
```

Expected: PASS.

- [ ] **Step 4: Review prompt boundaries manually**

Run:

```bash
rtk rg -n "Pinduoduo|Taobao|Tmall|JD|Xiaohongshu|Douyin|selling point|marketplace|platform style" backend/app/agent_openai.py backend/app/image_prompts.py backend/app/agent_tools.py
```

Expected: matches only in product prompt content or product boundary tests, not in ChatGPT general prompt content.

- [ ] **Step 5: Commit verification notes if needed**

If the implementation added docs or verification notes:

```bash
rtk git add docs/plans
rtk git commit -m "docs: record two tool prompt verification"
```

Otherwise skip commit.

---

## Self-Review

- Spec coverage: The plan covers separate ChatGPT and product prompts, ChatGPT pure text-to-image, ChatGPT image editing, product prompt separation, high quality output, and prompt boundary tests.
- Placeholder scan: No task uses TBD, TODO, or unspecified test instructions.
- Type consistency: `answer/generate/edit`, `chatgpt_image_generate`, `chatgpt_image_edit`, and `ChatGptImageBrief` are introduced before later tasks depend on them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-two-tool-image-prompt-system.md`. Two execution options:

**1. Subagent-Driven (recommended)** - dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - execute tasks in this session using executing-plans, batch execution with checkpoints.

Choose an approach before implementation starts.
