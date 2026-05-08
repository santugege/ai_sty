from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import cast

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.tools import (
    ImageSize,
    ImageTool,
    ProductImagePurposeId,
    ProductPlatformStyleId,
    get_product_image_purpose,
    get_product_platform_style,
    get_tool_by_id,
)

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


@dataclass(frozen=True)
class ValidImageRequest:
    tool: ImageTool
    prompt: str
    size: ImageSize
    image_bytes: bytes | None = None
    image_name: str | None = None
    image_type: str | None = None
    product_fields: ProductImageFields | None = None


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

    return ValidImageRequest(
        tool=tool,
        prompt=normalized_prompt,
        size=normalized_size,
        image_bytes=image_bytes,
        image_name=image_name,
        image_type=image_type,
        product_fields=product_fields,
    )


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

    normalized_product_fields = [
        normalize_text(value)
        for value in (
            platform_style,
            image_purpose,
            product_category,
            selling_points,
            scene_style,
            visual_tone,
            promotion_text,
            preserve_requirements,
            avoid_elements,
        )
    ]
    if not any(normalized_product_fields):
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


def validate_uploaded_image_content(image_bytes: bytes, image_type: str) -> None:
    try:
        with Image.open(BytesIO(image_bytes)) as uploaded_image:
            image_format = (uploaded_image.format or "").upper()
            uploaded_image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ImageRequestError(400, INVALID_IMAGE_MESSAGE) from None

    if image_format != SUPPORTED_IMAGE_FORMATS_BY_TYPE.get(image_type):
        raise ImageRequestError(400, INVALID_IMAGE_MESSAGE)
