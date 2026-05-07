import asyncio
from io import BytesIO

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.image_request import (
    MAX_IMAGE_BYTES,
    SUPPORTED_IMAGE_TYPES,
    ImageRequestError,
    compose_tool_prompt,
    validate_image_form,
)
from app.tools import get_tool_by_id


def run(coro):
    return asyncio.run(coro)


def upload_file(content_type="image/png", data=b"image-bytes", filename="input.png"):
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


def test_requires_server_api_key():
    try:
        run(validate_image_form("creator", "a quiet studio", "1024x1024", None, None))
    except ImageRequestError as error:
        assert error.status_code == 500
        assert error.message == "服务器未配置 OPENAI_API_KEY。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_unknown_tool_id():
    try:
        run(validate_image_form("missing", "a quiet studio", "1024x1024", None, "key"))
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请选择有效的图片工具。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_empty_required_prompt():
    try:
        run(validate_image_form("creator", "   ", "1024x1024", None, "key"))
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请输入画面描述。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_requires_upload_for_old_photo_restoration():
    try:
        run(validate_image_form("restore", "修复划痕", "1024x1024", None, "key"))
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请上传旧照片。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_unsupported_file_types():
    try:
        run(
            validate_image_form(
                "restore",
                "修复划痕",
                "1024x1024",
                upload_file(content_type="image/gif"),
                "key",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "图片格式仅支持 PNG、JPG 或 WebP。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_oversized_uploads():
    try:
        run(
            validate_image_form(
                "restore",
                "修复划痕",
                "1024x1024",
                upload_file(data=b"x" * (MAX_IMAGE_BYTES + 1)),
                "key",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "图片不能超过 10MB。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_returns_normalized_valid_request():
    result = run(
        validate_image_form(
            "restore",
            " 修复划痕 ",
            "1536x1024",
            upload_file(content_type="image/jpeg", filename="photo.jpg"),
            "key",
        )
    )

    assert result.tool.id == "restore"
    assert result.prompt == "修复划痕"
    assert result.size == "1536x1024"
    assert result.image_bytes == b"image-bytes"
    assert result.image_name == "photo.jpg"
    assert result.image_type == "image/jpeg"


def test_falls_back_to_default_size_for_invalid_size_input():
    result = run(validate_image_form("creator", "a quiet studio", "800x800", None, "key"))

    assert result.size == "1024x1024"


def test_compose_tool_prompt_combines_base_prompt_with_user_instructions():
    tool = get_tool_by_id("product")
    prompt = compose_tool_prompt(tool, "放在现代厨房里")

    assert tool.base_prompt in prompt
    assert "User request:" in prompt
    assert "放在现代厨房里" in prompt


def test_compose_tool_prompt_uses_base_prompt_when_optional_prompt_empty():
    tool = get_tool_by_id("restore")

    assert compose_tool_prompt(tool, "   ") == tool.base_prompt


def test_documents_supported_upload_types():
    assert SUPPORTED_IMAGE_TYPES == ("image/png", "image/jpeg", "image/webp")
