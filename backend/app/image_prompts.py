from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    product_fields: Any,
    generation_settings: Any,
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


def _product_brief_lines(
    product_fields: Any,
    user_prompt: str,
    generation_settings: Any,
) -> list[str]:
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
