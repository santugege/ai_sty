from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.tools import ImageSize, ImageTool, get_tool_by_id

MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp")
SUPPORTED_IMAGE_FORMATS_BY_TYPE = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
    "image/webp": "WEBP",
}
INVALID_IMAGE_MESSAGE = "图片内容不是有效的 PNG、JPG 或 WebP。"


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
    if not (api_key or "").strip():
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
        if tool.mode == "generate":
            raise ImageRequestError(400, "该工具不支持上传图片。")

        image_bytes = await image.read(MAX_IMAGE_BYTES + 1)

        if not image_bytes:
            raise ImageRequestError(400, "上传的图片为空。")

        image_type = image.content_type or ""
        image_name = image.filename

        if image_type not in SUPPORTED_IMAGE_TYPES:
            raise ImageRequestError(400, "图片格式仅支持 PNG、JPG 或 WebP。")

        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ImageRequestError(400, "图片不能超过 10MB。")

        validate_uploaded_image_content(image_bytes, image_type)

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


def validate_uploaded_image_content(image_bytes: bytes, image_type: str) -> None:
    try:
        with Image.open(BytesIO(image_bytes)) as uploaded_image:
            image_format = (uploaded_image.format or "").upper()
            uploaded_image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ImageRequestError(400, INVALID_IMAGE_MESSAGE) from None

    if image_format != SUPPORTED_IMAGE_FORMATS_BY_TYPE.get(image_type):
        raise ImageRequestError(400, INVALID_IMAGE_MESSAGE)
