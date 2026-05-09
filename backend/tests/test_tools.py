from app.tools import (
    get_product_image_purpose,
    get_product_platform_style,
    get_tool_by_id,
    image_sizes,
    image_tools,
    is_image_size,
    product_image_purposes,
    product_platform_styles,
)


def test_defines_only_product_tool():
    assert [tool.id for tool in image_tools] == ["product"]


def test_product_tool_is_edit_capable():
    assert get_tool_by_id("product").mode == "edit"


def test_product_tool_requires_upload():
    assert get_tool_by_id("product").image_required is True


def test_removed_tools_are_not_available():
    assert get_tool_by_id("creator") is None
    assert get_tool_by_id("restore") is None
    assert get_tool_by_id("avatar") is None
    assert get_tool_by_id("missing") is None


def test_accepts_only_configured_image_sizes():
    assert image_sizes == ("1024x1024", "1536x1024", "1024x1536")
    assert is_image_size("1536x1024") is True
    assert is_image_size("800x800") is False


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
