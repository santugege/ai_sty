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
