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
