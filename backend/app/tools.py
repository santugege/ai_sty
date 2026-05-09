from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ImageSize = Literal[
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "2048x2048",
    "2048x1152",
    "3840x2160",
    "2160x3840",
]
ToolMode = Literal["generate"]
ToolId = Literal["product"]
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

image_sizes: tuple[ImageSize, ...] = (
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "2048x2048",
    "2048x1152",
    "3840x2160",
    "2160x3840",
)

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
        id="product",
        title="商品图生成",
        mode="generate",
        prompt_label="商品场景",
        prompt_required=False,
        image_required=False,
        image_label="上传商品图",
        default_size="1536x1024",
        size_options=image_sizes,
        base_prompt=(
            "Generate a clean ecommerce product visual. If a product image is "
            "provided, preserve the product shape, color, logo, and important "
            "details while changing the scene as requested. If no product image "
            "is provided, create a commercially usable ecommerce direction draft "
            "from the platform, purpose, aspect ratio, size, and user brief."
        ),
    ),
)


def get_tool_by_id(tool_id: str) -> ImageTool | None:
    return next((tool for tool in image_tools if tool.id == tool_id), None)


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


def is_image_size(value: str) -> bool:
    return value in image_sizes
