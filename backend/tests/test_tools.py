from app.tools import (
    get_product_image_purpose,
    get_product_platform_style,
    get_tool_by_id,
    image_sizes,
    image_tools,
    product_image_purposes,
    product_platform_styles,
)


def test_defines_only_product_tool():
    assert [tool.id for tool in image_tools] == ["product"]


def test_product_tool_keeps_only_product_runtime_fields():
    tool = get_tool_by_id("product")

    assert tool.title == "商品图生成"
    assert tool.default_size == "1536x1024"
    assert tool.size_options == image_sizes
    assert "If no product image" not in tool.base_prompt
    assert not hasattr(tool, "mode")
    assert not hasattr(tool, "prompt_label")
    assert not hasattr(tool, "prompt_required")
    assert not hasattr(tool, "image_required")
    assert not hasattr(tool, "image_label")


def test_removed_tools_are_not_available():
    assert get_tool_by_id("creator") is None
    assert get_tool_by_id("restore") is None
    assert get_tool_by_id("avatar") is None
    assert get_tool_by_id("missing") is None


def test_accepts_only_configured_image_sizes():
    assert image_sizes == (
        "1024x1024",
        "1536x1024",
        "1024x1536",
        "2048x2048",
        "2048x1152",
        "3840x2160",
        "2160x3840",
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
