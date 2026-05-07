# Image Toolbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js image toolbox website backed by a Python FastAPI service that calls OpenAI image models without exposing `OPENAI_API_KEY` to the browser.

**Architecture:** The project is split into `frontend/` and `backend/`. The Next.js frontend renders the toolbox and submits `FormData` to the FastAPI backend; the backend validates requests, composes prompts, calls the OpenAI Python SDK, and returns stable JSON image results or errors.

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS, lucide-react, FastAPI, OpenAI Python SDK, pytest.

---

## File Structure

- Create `backend/requirements.txt`: Python backend dependencies.
- Create `backend/.env.example`: backend environment variables.
- Create `backend/pytest.ini`: pytest discovery and import path.
- Create `backend/app/__init__.py`: backend package marker.
- Create `backend/app/tools.py`: backend tool registry.
- Create `backend/app/image_request.py`: request validation and prompt composition.
- Create `backend/app/openai_images.py`: OpenAI image API wrapper.
- Create `backend/app/main.py`: FastAPI app, CORS, health route, and image route.
- Create `backend/tests/test_tools.py`: backend tool registry tests.
- Create `backend/tests/test_image_request.py`: validation tests.
- Create `backend/tests/test_openai_images.py`: OpenAI wrapper tests.
- Create `backend/tests/test_main.py`: FastAPI route tests.
- Create `frontend/package.json`: frontend project metadata and scripts.
- Create `frontend/tsconfig.json`: strict TypeScript setup for Next.js.
- Create `frontend/next.config.ts`: Next.js configuration.
- Create `frontend/postcss.config.mjs`: Tailwind CSS PostCSS integration.
- Create `frontend/eslint.config.mjs`: flat ESLint configuration.
- Create `frontend/.env.example`: frontend API base URL.
- Create `frontend/src/app/layout.tsx`: root HTML shell and metadata.
- Create `frontend/src/app/globals.css`: Tailwind import, theme tokens, and base styles.
- Create `frontend/src/lib/tools.ts`: frontend display registry.
- Create `frontend/src/components/tool-card.tsx`: reusable homepage card.
- Create `frontend/src/components/tool-form.tsx`: client-side form, upload, submit state, result, and errors.
- Create `frontend/src/app/page.tsx`: toolbox homepage.
- Create `frontend/src/app/tools/[toolId]/page.tsx`: dynamic tool page.

---

### Task 1: Python Backend Scaffold and Tool Registry

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/tools.py`
- Create: `backend/tests/test_tools.py`

- [ ] **Step 1: Create backend dependency and test config files**

Write `backend/requirements.txt`:

```txt
fastapi
uvicorn[standard]
openai
python-dotenv
python-multipart
pytest
httpx
```

Write `backend/.env.example`:

```bash
OPENAI_API_KEY=
OPENAI_IMAGE_MODEL=gpt-image-2
FRONTEND_ORIGIN=http://localhost:3000
```

Write `backend/pytest.ini`:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

Write `backend/app/__init__.py`:

```python
"""Image toolbox FastAPI backend."""
```

- [ ] **Step 2: Install backend dependencies**

Run:

```bash
rtk python -m venv backend/.venv
rtk backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
```

Expected: dependencies install successfully and `backend/.venv/` remains ignored by Git.

- [ ] **Step 3: Write failing tool registry tests**

Write `backend/tests/test_tools.py`:

```python
from app.tools import get_tool_by_id, image_sizes, image_tools, is_image_size


def test_defines_four_launch_tools_in_display_order():
    assert [tool.id for tool in image_tools] == [
        "creator",
        "restore",
        "avatar",
        "product",
    ]


def test_marks_creator_as_generation_and_others_as_edit_capable():
    assert get_tool_by_id("creator").mode == "generate"
    assert get_tool_by_id("restore").mode == "edit"
    assert get_tool_by_id("avatar").mode == "edit"
    assert get_tool_by_id("product").mode == "edit"


def test_requires_uploads_only_for_restore_and_product():
    assert get_tool_by_id("creator").image_required is False
    assert get_tool_by_id("restore").image_required is True
    assert get_tool_by_id("avatar").image_required is False
    assert get_tool_by_id("product").image_required is True


def test_finds_known_tools_and_rejects_unknown_ids():
    assert get_tool_by_id("avatar").title == "头像/写真生成"
    assert get_tool_by_id("missing") is None


def test_accepts_only_configured_image_sizes():
    assert image_sizes == ("1024x1024", "1536x1024", "1024x1536")
    assert is_image_size("1536x1024") is True
    assert is_image_size("800x800") is False
```

- [ ] **Step 4: Run tests to verify failure**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_tools.py -q
```

Expected: FAIL because `backend/app/tools.py` does not exist.

- [ ] **Step 5: Implement backend tool registry**

Write `backend/app/tools.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ImageSize = Literal["1024x1024", "1536x1024", "1024x1536"]
ToolMode = Literal["generate", "edit"]
ToolId = Literal["creator", "restore", "avatar", "product"]

image_sizes: tuple[ImageSize, ...] = ("1024x1024", "1536x1024", "1024x1536")


@dataclass(frozen=True)
class ImageTool:
    id: ToolId
    title: str
    mode: ToolMode
    prompt_label: str
    prompt_required: bool
    image_required: bool
    image_label: str
    default_size: ImageSize
    size_options: tuple[ImageSize, ...]
    base_prompt: str


image_tools: tuple[ImageTool, ...] = (
    ImageTool(
        id="creator",
        title="AI 图片创作",
        mode="generate",
        prompt_label="画面描述",
        prompt_required=True,
        image_required=False,
        image_label="参考图",
        default_size="1024x1024",
        size_options=image_sizes,
        base_prompt=(
            "Create a polished, original image that follows the user's visual "
            "description. Prioritize clear composition, coherent lighting, and "
            "a finished professional look."
        ),
    ),
    ImageTool(
        id="restore",
        title="老照片修复",
        mode="edit",
        prompt_label="修复要求",
        prompt_required=False,
        image_required=True,
        image_label="上传旧照片",
        default_size="1024x1024",
        size_options=image_sizes,
        base_prompt=(
            "Restore the uploaded old photo. Preserve the original identity, "
            "pose, clothing, and historical character. Repair scratches, fading, "
            "stains, and blur while keeping the result natural."
        ),
    ),
    ImageTool(
        id="avatar",
        title="头像/写真生成",
        mode="edit",
        prompt_label="头像风格",
        prompt_required=True,
        image_required=False,
        image_label="上传参考图",
        default_size="1024x1024",
        size_options=("1024x1024", "1024x1536"),
        base_prompt=(
            "Create a refined portrait or avatar. If a reference image is "
            "provided, preserve the person's core facial identity while applying "
            "the requested style."
        ),
    ),
    ImageTool(
        id="product",
        title="商品图生成",
        mode="edit",
        prompt_label="商品场景",
        prompt_required=False,
        image_required=True,
        image_label="上传商品图",
        default_size="1536x1024",
        size_options=image_sizes,
        base_prompt=(
            "Generate a clean ecommerce product visual from the uploaded product "
            "image. Preserve the product shape, color, logo, and important "
            "details while changing the scene as requested."
        ),
    ),
)


def get_tool_by_id(tool_id: str) -> ImageTool | None:
    return next((tool for tool in image_tools if tool.id == tool_id), None)


def is_image_size(value: str) -> bool:
    return value in image_sizes
```

- [ ] **Step 6: Run registry tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_tools.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit backend scaffold and registry**

Run:

```bash
rtk git add backend/requirements.txt backend/.env.example backend/pytest.ini backend/app/__init__.py backend/app/tools.py backend/tests/test_tools.py
rtk git commit -m "feat: scaffold fastapi backend registry"
```

Expected: commit succeeds.

---

### Task 2: Backend Request Validation

**Files:**
- Create: `backend/app/image_request.py`
- Create: `backend/tests/test_image_request.py`

- [ ] **Step 1: Write failing validation tests**

Write `backend/tests/test_image_request.py`:

```python
import asyncio
from io import BytesIO

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.image_request import (
    MAX_IMAGE_BYTES,
    SUPPORTED_IMAGE_TYPES,
    ImageRequestError,
    compose_tool_prompt,
    validate_image_form,
)
from app.tools import get_tool_by_id


def run(coro):
    return asyncio.run(coro)


def upload_file(content_type="image/png", data=b"image-bytes", filename="input.png"):
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


def test_requires_server_api_key():
    try:
        run(validate_image_form("creator", "a quiet studio", "1024x1024", None, None))
    except ImageRequestError as error:
        assert error.status_code == 500
        assert error.message == "服务器未配置 OPENAI_API_KEY。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_unknown_tool_id():
    try:
        run(validate_image_form("missing", "a quiet studio", "1024x1024", None, "key"))
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请选择有效的图片工具。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_empty_required_prompt():
    try:
        run(validate_image_form("creator", "   ", "1024x1024", None, "key"))
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请输入画面描述。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_requires_upload_for_old_photo_restoration():
    try:
        run(validate_image_form("restore", "修复划痕", "1024x1024", None, "key"))
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请上传旧照片。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_unsupported_file_types():
    try:
        run(
            validate_image_form(
                "restore",
                "修复划痕",
                "1024x1024",
                upload_file(content_type="image/gif"),
                "key",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "图片格式仅支持 PNG、JPG 或 WebP。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_oversized_uploads():
    try:
        run(
            validate_image_form(
                "restore",
                "修复划痕",
                "1024x1024",
                upload_file(data=b"x" * (MAX_IMAGE_BYTES + 1)),
                "key",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "图片不能超过 10MB。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_returns_normalized_valid_request():
    result = run(
        validate_image_form(
            "restore",
            " 修复划痕 ",
            "1536x1024",
            upload_file(content_type="image/jpeg", filename="photo.jpg"),
            "key",
        )
    )

    assert result.tool.id == "restore"
    assert result.prompt == "修复划痕"
    assert result.size == "1536x1024"
    assert result.image_bytes == b"image-bytes"
    assert result.image_name == "photo.jpg"
    assert result.image_type == "image/jpeg"


def test_falls_back_to_default_size_for_invalid_size_input():
    result = run(validate_image_form("creator", "a quiet studio", "800x800", None, "key"))

    assert result.size == "1024x1024"


def test_compose_tool_prompt_combines_base_prompt_with_user_instructions():
    tool = get_tool_by_id("product")
    prompt = compose_tool_prompt(tool, "放在现代厨房里")

    assert tool.base_prompt in prompt
    assert "User request:" in prompt
    assert "放在现代厨房里" in prompt


def test_compose_tool_prompt_uses_base_prompt_when_optional_prompt_empty():
    tool = get_tool_by_id("restore")

    assert compose_tool_prompt(tool, "   ") == tool.base_prompt


def test_documents_supported_upload_types():
    assert SUPPORTED_IMAGE_TYPES == ("image/png", "image/jpeg", "image/webp")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_request.py -q
```

Expected: FAIL because `backend/app/image_request.py` does not exist.

- [ ] **Step 3: Implement validation and prompt composition**

Write `backend/app/image_request.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from fastapi import UploadFile

from app.tools import ImageSize, ImageTool, get_tool_by_id

MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp")


class ImageRequestError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ValidImageRequest:
    tool: ImageTool
    prompt: str
    size: ImageSize
    image_bytes: bytes | None = None
    image_name: str | None = None
    image_type: str | None = None


async def validate_image_form(
    tool_id: str | None,
    prompt: str | None,
    size: str | None,
    image: UploadFile | None,
    api_key: str | None,
) -> ValidImageRequest:
    if not api_key:
        raise ImageRequestError(500, "服务器未配置 OPENAI_API_KEY。")

    tool = get_tool_by_id((tool_id or "").strip())
    if tool is None:
        raise ImageRequestError(400, "请选择有效的图片工具。")

    normalized_prompt = (prompt or "").strip()
    if tool.prompt_required and not normalized_prompt:
        raise ImageRequestError(400, f"请输入{tool.prompt_label}。")

    image_bytes: bytes | None = None
    image_name: str | None = None
    image_type: str | None = None

    if image is not None and image.filename:
        image_bytes = await image.read()

        if image_bytes:
            image_type = image.content_type or ""
            image_name = image.filename

            if image_type not in SUPPORTED_IMAGE_TYPES:
                raise ImageRequestError(400, "图片格式仅支持 PNG、JPG 或 WebP。")

            if len(image_bytes) > MAX_IMAGE_BYTES:
                raise ImageRequestError(400, "图片不能超过 10MB。")
        else:
            image_bytes = None

    if tool.image_required and image_bytes is None:
        raise ImageRequestError(400, f"请{tool.image_label}。")

    requested_size = (size or "").strip()
    normalized_size = (
        requested_size if requested_size in tool.size_options else tool.default_size
    )

    return ValidImageRequest(
        tool=tool,
        prompt=normalized_prompt,
        size=normalized_size,
        image_bytes=image_bytes,
        image_name=image_name,
        image_type=image_type,
    )


def compose_tool_prompt(tool: ImageTool, user_prompt: str) -> str:
    normalized_prompt = user_prompt.strip()

    if not normalized_prompt:
        return tool.base_prompt

    return f"{tool.base_prompt}\n\nUser request:\n{normalized_prompt}"
```

- [ ] **Step 4: Run validation tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_image_request.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit validation**

Run:

```bash
rtk git add backend/app/image_request.py backend/tests/test_image_request.py
rtk git commit -m "feat: validate backend image requests"
```

Expected: commit succeeds.

---

### Task 3: OpenAI Wrapper and FastAPI Route

**Files:**
- Create: `backend/app/openai_images.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_openai_images.py`
- Create: `backend/tests/test_main.py`

- [ ] **Step 1: Write failing OpenAI wrapper tests**

Write `backend/tests/test_openai_images.py`:

```python
from types import SimpleNamespace

import pytest

from app.image_request import ValidImageRequest
from app.openai_images import normalize_openai_image_response, request_image_from_openai
from app.tools import get_tool_by_id


def test_normalizes_base64_image_data():
    result = normalize_openai_image_response(
        {"data": [{"b64_json": "abc123", "revised_prompt": "a refined prompt"}]}
    )

    assert result.src == "data:image/png;base64,abc123"
    assert result.mime_type == "image/png"
    assert result.revised_prompt == "a refined prompt"


def test_normalizes_hosted_image_url():
    result = normalize_openai_image_response(
        SimpleNamespace(data=[SimpleNamespace(url="https://example.test/image.png")])
    )

    assert result.src == "https://example.test/image.png"
    assert result.mime_type == "image/png"
    assert result.revised_prompt is None


def test_raises_stable_error_when_no_image_is_returned():
    with pytest.raises(RuntimeError, match="OpenAI 没有返回图片结果。"):
        normalize_openai_image_response({"data": []})


def test_requests_text_generation_without_uploaded_image():
    class FakeImages:
        def __init__(self):
            self.generate_kwargs = None
            self.edit_kwargs = None

        def generate(self, **kwargs):
            self.generate_kwargs = kwargs
            return {"data": [{"b64_json": "abc123"}]}

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "should-not-happen"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("creator"),
            prompt="a quiet studio",
            size="1024x1024",
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.src == "data:image/png;base64,abc123"
    assert fake_client.images.generate_kwargs["model"] == "gpt-image-2"
    assert "a quiet studio" in fake_client.images.generate_kwargs["prompt"]
    assert fake_client.images.generate_kwargs["size"] == "1024x1024"
    assert fake_client.images.edit_kwargs is None


def test_requests_image_edit_when_uploaded_image_is_present():
    class FakeImages:
        def __init__(self):
            self.edit_kwargs = None

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "edited"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("restore"),
            prompt="修复划痕",
            size="1024x1024",
            image_bytes=b"image-bytes",
            image_name="photo.png",
            image_type="image/png",
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.src == "data:image/png;base64,edited"
    assert fake_client.images.edit_kwargs["model"] == "gpt-image-2"
    assert fake_client.images.edit_kwargs["image"].name == "photo.png"
    assert "修复划痕" in fake_client.images.edit_kwargs["prompt"]
```

- [ ] **Step 2: Run wrapper tests to verify failure**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_openai_images.py -q
```

Expected: FAIL because `backend/app/openai_images.py` does not exist.

- [ ] **Step 3: Implement the OpenAI wrapper**

Write `backend/app/openai_images.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable

from openai import OpenAI

from app.image_request import ValidImageRequest, compose_tool_prompt


@dataclass(frozen=True)
class GeneratedImageResult:
    src: str
    mime_type: str = "image/png"
    revised_prompt: str | None = None


def request_image_from_openai(
    request: ValidImageRequest,
    api_key: str,
    model: str,
    client_factory: Callable[..., Any] = OpenAI,
) -> GeneratedImageResult:
    client = client_factory(api_key=api_key)
    prompt = compose_tool_prompt(request.tool, request.prompt)

    if request.image_bytes:
        image_file = BytesIO(request.image_bytes)
        image_file.name = request.image_name or "input.png"
        response = client.images.edit(
            model=model,
            image=image_file,
            prompt=prompt,
            size=request.size,
            quality="auto",
        )
        return normalize_openai_image_response(response)

    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=request.size,
        quality="auto",
    )
    return normalize_openai_image_response(response)


def normalize_openai_image_response(response: Any) -> GeneratedImageResult:
    data = _read(response, "data") or []
    image = data[0] if data else None

    if image is None:
        raise RuntimeError("OpenAI 没有返回图片结果。")

    b64_json = _read(image, "b64_json")
    revised_prompt = _read(image, "revised_prompt")

    if b64_json:
        return GeneratedImageResult(
            src=f"data:image/png;base64,{b64_json}",
            revised_prompt=revised_prompt,
        )

    url = _read(image, "url")
    if url:
        return GeneratedImageResult(src=url, revised_prompt=revised_prompt)

    raise RuntimeError("OpenAI 没有返回图片结果。")


def _read(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
```

- [ ] **Step 4: Run wrapper tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_openai_images.py -q
```

Expected: PASS.

- [ ] **Step 5: Write failing FastAPI route tests**

Write `backend/tests/test_main.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.openai_images import GeneratedImageResult


client = TestClient(app)


def test_health_route_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_image_route_returns_missing_key_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "a quiet studio", "size": "1024x1024"},
    )

    assert response.status_code == 500
    assert response.json() == {"error": "服务器未配置 OPENAI_API_KEY。"}


def test_image_route_returns_validation_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "   ", "size": "1024x1024"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "请输入画面描述。"}


def test_image_route_returns_generated_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def fake_request_image_from_openai(valid_request, api_key, model):
        assert valid_request.tool.id == "creator"
        assert valid_request.prompt == "a quiet studio"
        assert api_key == "key"
        assert model == "gpt-image-2"
        return GeneratedImageResult(src="data:image/png;base64,abc123")

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "a quiet studio", "size": "1024x1024"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "image": {
            "src": "data:image/png;base64,abc123",
            "mimeType": "image/png",
            "revisedPrompt": None,
        }
    }
```

- [ ] **Step 6: Run route tests to verify failure**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests/test_main.py -q
```

Expected: FAIL because `backend/app/main.py` does not exist.

- [ ] **Step 7: Implement FastAPI app and image route**

Write `backend/app/main.py`:

```python
from __future__ import annotations

import logging
import os
from dataclasses import asdict

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.image_request import ImageRequestError, validate_image_form
from app.openai_images import request_image_from_openai

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Image Toolbox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/images/generate")
async def generate_image(
    toolId: str = Form(...),
    prompt: str = Form(""),
    size: str = Form(""),
    image: UploadFile | None = File(None),
):
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        valid_request = await validate_image_form(toolId, prompt, size, image, api_key)
        generated = request_image_from_openai(
            valid_request,
            api_key=api_key or "",
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        )
        payload = asdict(generated)
        return {
            "image": {
                "src": payload["src"],
                "mimeType": payload["mime_type"],
                "revisedPrompt": payload["revised_prompt"],
            }
        }
    except ImageRequestError as error:
        return JSONResponse({"error": error.message}, status_code=error.status_code)
    except Exception as error:
        logger.exception("Image generation failed")
        return JSONResponse(
            {"error": public_error_message(error)},
            status_code=502,
        )


def public_error_message(error: Exception) -> str:
    message = str(error)

    if "content policy" in message.lower() or "safety" in message.lower():
        return "请求未通过图片安全审核，请调整描述后重试。"

    if message == "OpenAI 没有返回图片结果。":
        return message

    return "图片生成失败，请稍后重试。"
```

- [ ] **Step 8: Run backend tests**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
```

Expected: PASS.

- [ ] **Step 9: Commit FastAPI integration**

Run:

```bash
rtk git add backend/app/openai_images.py backend/app/main.py backend/tests/test_openai_images.py backend/tests/test_main.py
rtk git commit -m "feat: add fastapi image generation route"
```

Expected: commit succeeds.

---

### Task 4: Frontend Scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/eslint.config.mjs`
- Create: `frontend/.env.example`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/globals.css`

- [ ] **Step 1: Create frontend package manifest**

Write `frontend/package.json`:

```json
{
  "name": "image-toolbox-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "eslint ."
  },
  "dependencies": {
    "lucide-react": "latest",
    "next": "latest",
    "react": "latest",
    "react-dom": "latest"
  },
  "devDependencies": {
    "@eslint/eslintrc": "latest",
    "@tailwindcss/postcss": "latest",
    "@types/node": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "eslint": "latest",
    "eslint-config-next": "latest",
    "tailwindcss": "latest",
    "typescript": "latest"
  }
}
```

- [ ] **Step 2: Install frontend dependencies**

Run:

```bash
rtk npm install --prefix frontend
```

Expected: `frontend/package-lock.json` is created and npm exits with code 0.

- [ ] **Step 3: Create frontend configuration**

Write `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "baseUrl": ".",
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Write `frontend/next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
```

Write `frontend/postcss.config.mjs`:

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

Write `frontend/eslint.config.mjs`:

```js
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
```

Write `frontend/.env.example`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 4: Create the root frontend app shell**

Write `frontend/src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Image Toolbox",
  description:
    "AI image creation, photo restoration, portraits, and product visuals powered by OpenAI image models.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
```

Write `frontend/src/app/globals.css`:

```css
@import "tailwindcss";

:root {
  color-scheme: light;
  --ink: #171717;
  --muted: #646464;
  --paper: #f7f3ea;
  --panel: #fffdf8;
  --line: #ddd5c7;
  --teal: #0f766e;
  --red: #be3b37;
  --blue: #2563eb;
  --gold: #b7791f;
}

* {
  box-sizing: border-box;
}

html {
  min-height: 100%;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.08), transparent 34%),
    linear-gradient(315deg, rgba(190, 59, 55, 0.08), transparent 32%),
    var(--paper);
}

body {
  min-height: 100vh;
  margin: 0;
  color: var(--ink);
  font-family: ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
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

::selection {
  color: white;
  background: var(--teal);
}
```

- [ ] **Step 5: Verify scaffold build reaches missing page error**

Run:

```bash
rtk npm run lint --prefix frontend
```

Expected: PASS or only reports that no page exists yet. If lint fails for a concrete syntax or config error, fix it before continuing.

- [ ] **Step 6: Commit frontend scaffold**

Run:

```bash
rtk git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/next.config.ts frontend/postcss.config.mjs frontend/eslint.config.mjs frontend/.env.example frontend/src/app/layout.tsx frontend/src/app/globals.css
rtk git commit -m "chore: scaffold next frontend"
```

Expected: commit succeeds.

---

### Task 5: Toolbox Frontend Pages and Forms

**Files:**
- Create: `frontend/src/lib/tools.ts`
- Create: `frontend/src/components/tool-card.tsx`
- Create: `frontend/src/components/tool-form.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/tools/[toolId]/page.tsx`

- [ ] **Step 1: Create frontend tool registry**

Write `frontend/src/lib/tools.ts`:

```ts
export const imageSizes = ["1024x1024", "1536x1024", "1024x1536"] as const;

export type ImageSize = (typeof imageSizes)[number];
export type ToolId = "creator" | "restore" | "avatar" | "product";
export type ToolMode = "generate" | "edit";
export type ToolIcon = "sparkles" | "wand" | "user" | "package";

export type ImageTool = {
  id: ToolId;
  title: string;
  eyebrow: string;
  description: string;
  mode: ToolMode;
  icon: ToolIcon;
  accent: "teal" | "red" | "blue" | "gold";
  promptLabel: string;
  promptPlaceholder: string;
  imageRequired: boolean;
  imageLabel: string;
  defaultSize: ImageSize;
  sizeOptions: ImageSize[];
  examples: string[];
};

export const imageTools: ImageTool[] = [
  {
    id: "creator",
    title: "AI 图片创作",
    eyebrow: "Text to image",
    description: "输入画面描述，生成完整原创图片。",
    mode: "generate",
    icon: "sparkles",
    accent: "teal",
    promptLabel: "画面描述",
    promptPlaceholder:
      "例如：一间清晨阳光里的木质咖啡馆，窗边有绿植，写实摄影风格",
    imageRequired: false,
    imageLabel: "参考图",
    defaultSize: "1024x1024",
    sizeOptions: [...imageSizes],
    examples: ["写实摄影", "儿童绘本", "电影海报", "水彩插画"],
  },
  {
    id: "restore",
    title: "老照片修复",
    eyebrow: "Photo restoration",
    description: "修复划痕、褪色、模糊和年代感损伤。",
    mode: "edit",
    icon: "wand",
    accent: "red",
    promptLabel: "修复要求",
    promptPlaceholder:
      "例如：保留人物五官和年代感，修复划痕，提升清晰度，恢复自然色彩",
    imageRequired: true,
    imageLabel: "上传旧照片",
    defaultSize: "1024x1024",
    sizeOptions: [...imageSizes],
    examples: ["黑白上色", "划痕修复", "清晰增强", "褪色恢复"],
  },
  {
    id: "avatar",
    title: "头像/写真生成",
    eyebrow: "Portrait studio",
    description: "用参考图或风格描述生成头像、写真和社媒形象。",
    mode: "edit",
    icon: "user",
    accent: "blue",
    promptLabel: "头像风格",
    promptPlaceholder:
      "例如：商务头像，深色西装，自然微笑，干净灰色背景，柔和棚拍光",
    imageRequired: false,
    imageLabel: "上传参考图",
    defaultSize: "1024x1024",
    sizeOptions: ["1024x1024", "1024x1536"],
    examples: ["商务头像", "证件照风格", "社媒头像", "电影感写真"],
  },
  {
    id: "product",
    title: "商品图生成",
    eyebrow: "Product visuals",
    description: "为商品换背景、做场景图和电商展示图。",
    mode: "edit",
    icon: "package",
    accent: "gold",
    promptLabel: "商品场景",
    promptPlaceholder:
      "例如：保留商品外观，放在浅色石材台面上，背景是现代厨房，自然日光",
    imageRequired: true,
    imageLabel: "上传商品图",
    defaultSize: "1536x1024",
    sizeOptions: [...imageSizes],
    examples: ["白底图", "生活方式场景", "节日背景", "电商主图"],
  },
];

export function getToolById(id: string): ImageTool | undefined {
  return imageTools.find((tool) => tool.id === id);
}
```

- [ ] **Step 2: Create reusable tool card component**

Write `frontend/src/components/tool-card.tsx`:

```tsx
import Link from "next/link";
import { PackageSearch, Sparkles, UserRound, Wand2 } from "lucide-react";
import type { ImageTool } from "@/lib/tools";

const iconMap = {
  sparkles: Sparkles,
  wand: Wand2,
  user: UserRound,
  package: PackageSearch,
};

const accentClasses = {
  teal: "border-teal-700/25 bg-teal-50 text-teal-900",
  red: "border-red-700/25 bg-red-50 text-red-900",
  blue: "border-blue-700/25 bg-blue-50 text-blue-900",
  gold: "border-amber-700/30 bg-amber-50 text-amber-950",
};

export function ToolCard({ tool }: { tool: ImageTool }) {
  const Icon = iconMap[tool.icon];

  return (
    <Link
      href={`/tools/${tool.id}`}
      className="group grid min-h-64 content-between rounded-lg border border-stone-300 bg-white/75 p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-stone-950 hover:shadow-xl"
    >
      <div>
        <div
          className={`mb-5 inline-flex h-12 w-12 items-center justify-center rounded-md border ${accentClasses[tool.accent]}`}
        >
          <Icon aria-hidden="true" className="h-6 w-6" />
        </div>
        <p className="text-sm uppercase tracking-[0.18em] text-stone-500">
          {tool.eyebrow}
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-tight text-stone-950">
          {tool.title}
        </h2>
        <p className="mt-4 text-base leading-7 text-stone-600">
          {tool.description}
        </p>
      </div>
      <div className="mt-8 flex flex-wrap gap-2">
        {tool.examples.map((example) => (
          <span
            key={example}
            className="rounded border border-stone-300 px-2.5 py-1 text-sm text-stone-600"
          >
            {example}
          </span>
        ))}
      </div>
    </Link>
  );
}
```

- [ ] **Step 3: Create client tool form component**

Write `frontend/src/components/tool-form.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import { AlertCircle, ImageIcon, Loader2, Upload } from "lucide-react";
import type { ImageSize, ImageTool } from "@/lib/tools";

type GeneratedImage = {
  src: string;
  mimeType: string;
  revisedPrompt?: string | null;
};

type ToolFormProps = {
  tool: ImageTool;
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export function ToolForm({ tool }: ToolFormProps) {
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState<ImageSize>(tool.defaultSize);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GeneratedImage | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fileLabel = useMemo(() => {
    if (!file) {
      return tool.imageRequired ? "请选择图片文件" : "可选上传参考图";
    }

    return file.name;
  }, [file, tool.imageRequired]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    setIsSubmitting(true);

    const formData = new FormData();
    formData.append("toolId", tool.id);
    formData.append("prompt", prompt);
    formData.append("size", size);

    if (file) {
      formData.append("image", file);
    }

    try {
      const response = await fetch(`${apiBaseUrl}/api/images/generate`, {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as {
        image?: GeneratedImage;
        error?: string;
      };

      if (!response.ok || !payload.image) {
        throw new Error(payload.error || "图片生成失败，请稍后重试。");
      }

      setResult(payload.image);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "图片生成失败，请稍后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-stone-300 bg-white/80 p-5 shadow-sm"
      >
        <label className="block text-sm font-semibold text-stone-900">
          {tool.promptLabel}
        </label>
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder={tool.promptPlaceholder}
          rows={7}
          className="mt-3 w-full resize-none rounded-md border border-stone-300 bg-white px-4 py-3 text-base leading-7 text-stone-950 outline-none transition focus:border-stone-950"
        />

        {(tool.imageRequired || tool.mode === "edit") && (
          <label className="mt-5 block">
            <span className="text-sm font-semibold text-stone-900">
              {tool.imageLabel}
            </span>
            <span className="mt-3 flex min-h-28 items-center gap-3 rounded-md border border-dashed border-stone-400 bg-stone-50 px-4 py-4 text-stone-600 transition hover:border-stone-950">
              <Upload aria-hidden="true" className="h-5 w-5 shrink-0" />
              <span className="min-w-0 truncate">{fileLabel}</span>
            </span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>
        )}

        <label className="mt-5 block text-sm font-semibold text-stone-900">
          输出尺寸
        </label>
        <select
          value={size}
          onChange={(event) => setSize(event.target.value as ImageSize)}
          className="mt-3 w-full rounded-md border border-stone-300 bg-white px-4 py-3 text-stone-950 outline-none transition focus:border-stone-950"
        >
          {tool.sizeOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>

        {error && (
          <div className="mt-5 flex gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
            <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-stone-950 px-5 py-3 text-base font-semibold text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-500"
        >
          {isSubmitting ? (
            <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
          ) : (
            <ImageIcon aria-hidden="true" className="h-5 w-5" />
          )}
          {isSubmitting ? "生成中" : "生成图片"}
        </button>
      </form>

      <section className="grid min-h-[34rem] place-items-center rounded-lg border border-stone-300 bg-stone-950 p-4 text-white shadow-sm">
        {result ? (
          <div className="w-full">
            <img
              src={result.src}
              alt={`${tool.title}生成结果`}
              className="mx-auto max-h-[32rem] w-auto max-w-full rounded-md object-contain"
            />
            {result.revisedPrompt && (
              <p className="mt-4 text-sm leading-6 text-stone-300">
                {result.revisedPrompt}
              </p>
            )}
          </div>
        ) : (
          <div className="max-w-sm text-center">
            <ImageIcon aria-hidden="true" className="mx-auto h-10 w-10 text-stone-400" />
            <p className="mt-4 text-xl font-semibold">结果会显示在这里</p>
            <p className="mt-3 text-sm leading-6 text-stone-400">
              提交后请等待图片模型完成生成，复杂图片可能需要较长时间。
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 4: Create homepage and dynamic tool pages**

Write `frontend/src/app/page.tsx`:

```tsx
import { ToolCard } from "@/components/tool-card";
import { imageTools } from "@/lib/tools";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-8 sm:px-8 lg:px-10">
      <header className="grid gap-6 border-b border-stone-300 pb-8 lg:grid-cols-[1fr_0.75fr] lg:items-end">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-stone-500">
            OpenAI image studio
          </p>
          <h1 className="mt-4 max-w-4xl text-5xl font-semibold leading-[1.04] text-stone-950 sm:text-6xl lg:text-7xl">
            图片生成工具箱
          </h1>
        </div>
        <p className="max-w-xl text-lg leading-8 text-stone-600">
          选择一个功能，输入描述或上传图片，由 Python 后端安全调用 OpenAI 图片模型生成结果。
        </p>
      </header>

      <section className="grid flex-1 gap-4 py-8 sm:grid-cols-2 xl:grid-cols-4">
        {imageTools.map((tool) => (
          <ToolCard key={tool.id} tool={tool} />
        ))}
      </section>
    </main>
  );
}
```

Write `frontend/src/app/tools/[toolId]/page.tsx`:

```tsx
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { notFound } from "next/navigation";
import { ToolForm } from "@/components/tool-form";
import { getToolById, imageTools } from "@/lib/tools";

type ToolPageProps = {
  params: Promise<{
    toolId: string;
  }>;
};

export function generateStaticParams() {
  return imageTools.map((tool) => ({
    toolId: tool.id,
  }));
}

export async function generateMetadata({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  return {
    title: tool ? `${tool.title} | Image Toolbox` : "Image Toolbox",
  };
}

export default async function ToolPage({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  if (!tool) {
    notFound();
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm font-semibold text-stone-600 transition hover:text-stone-950"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        返回工具箱
      </Link>

      <header className="mt-8 grid gap-5 border-b border-stone-300 pb-8 lg:grid-cols-[1fr_0.72fr] lg:items-end">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-stone-500">
            {tool.eyebrow}
          </p>
          <h1 className="mt-4 text-5xl font-semibold leading-tight text-stone-950">
            {tool.title}
          </h1>
        </div>
        <p className="max-w-xl text-lg leading-8 text-stone-600">
          {tool.description}
        </p>
      </header>

      <section className="py-8">
        <ToolForm tool={tool} />
      </section>
    </main>
  );
}
```

- [ ] **Step 5: Run frontend lint and build**

Run:

```bash
rtk npm run lint --prefix frontend
rtk npm run build --prefix frontend
```

Expected: both commands exit with code 0 and the build lists `/` and `/tools/[toolId]`.

- [ ] **Step 6: Commit frontend toolbox**

Run:

```bash
rtk git add frontend/src/lib/tools.ts frontend/src/components/tool-card.tsx frontend/src/components/tool-form.tsx frontend/src/app/page.tsx frontend/src/app/tools/[toolId]/page.tsx
rtk git commit -m "feat: build image toolbox frontend"
```

Expected: commit succeeds.

---

### Task 6: Final Verification and Local Run

**Files:**
- Modify only if verification reveals a concrete defect in files from earlier tasks.

- [ ] **Step 1: Run complete automated checks**

Run:

```bash
rtk backend/.venv/Scripts/python -m pytest backend/tests -q
rtk npm run lint --prefix frontend
rtk npm run build --prefix frontend
```

Expected: all commands exit with code 0.

- [ ] **Step 2: Verify missing API key behavior through FastAPI**

Run the backend without `OPENAI_API_KEY`:

```bash
rtk backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another shell, run:

```bash
rtk powershell -NoProfile -Command "Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/images/generate' -Form @{ toolId='creator'; prompt='a quiet studio'; size='1024x1024' }"
```

Expected: HTTP 500 JSON response with `服务器未配置 OPENAI_API_KEY。`.

- [ ] **Step 3: Verify frontend can reach backend errors**

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Run the frontend:

```bash
rtk npm run dev --prefix frontend
```

Open `http://localhost:3000/tools/creator`, submit `a quiet studio` while the backend has no `OPENAI_API_KEY`.

Expected: the form displays `服务器未配置 OPENAI_API_KEY。`.

- [ ] **Step 4: Verify one real OpenAI image request**

Create `backend/.env`:

```bash
OPENAI_API_KEY=<actual OpenAI API key from the deployment environment>
OPENAI_IMAGE_MODEL=gpt-image-2
FRONTEND_ORIGIN=http://localhost:3000
```

Restart the backend:

```bash
rtk backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Open `http://localhost:3000/tools/creator`, submit:

```text
一张产品级网页配图：玻璃桌面上的复古相机，清晨自然光，浅景深，真实摄影风格
```

Expected: the result panel displays a generated image.

- [ ] **Step 5: Commit verification fixes if any were needed**

If files changed during verification, run:

```bash
rtk git status --short
rtk git add <changed-files>
rtk git commit -m "fix: polish image toolbox verification issues"
```

Expected: commit succeeds when there are changes. If no files changed, skip the commit.

---

## Self-Review

Spec coverage:

- Toolbox homepage with four feature cards: Task 5.
- Separate configurable tool pages: Task 5.
- Python backend with FastAPI: Tasks 1, 2, and 3.
- Server-side `OPENAI_API_KEY`: Tasks 2, 3, and 6.
- OpenAI Python SDK integration: Task 3.
- Text generation and image editing flows: Tasks 2 and 3.
- Stable backend JSON errors and frontend error display: Tasks 2, 3, 5, and 6.
- Backend tests, frontend lint, frontend build, and real API verification: Task 6.

Placeholder scan:

- The plan contains no unfinished implementation placeholders.
- Every created source file has concrete content.
- Commands and expected results are explicit.
- The only value the implementer must supply is the real secret in `backend/.env` during manual verification.

Type consistency:

- Backend tool ids match frontend tool ids.
- `ValidImageRequest` is returned by validation and consumed by `request_image_from_openai`.
- `GeneratedImageResult` maps to frontend `{ src, mimeType, revisedPrompt }`.
- Frontend posts `toolId`, `prompt`, `size`, and optional `image`, matching FastAPI route parameters.

