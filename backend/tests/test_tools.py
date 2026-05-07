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
