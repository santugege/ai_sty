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
        "product photo",
        "promotion",
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
