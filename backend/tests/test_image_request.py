import asyncio
import base64
from io import BytesIO

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.image_request import (
    MAX_IMAGE_BYTES,
    SUPPORTED_IMAGE_TYPES,
    ProductGenerationSettings,
    ImageRequestError,
    ProductImageFields,
    compose_tool_prompt,
    validate_image_form,
)
from app.tools import get_tool_by_id

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+p5qgoAAAAABJRU5ErkJggg=="
)
BROKEN_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def run(coro):
    return asyncio.run(coro)


def upload_file(content_type="image/png", data=TINY_PNG, filename="input.png"):
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


class RecordingUpload:
    filename = "large.png"
    content_type = "image/png"

    def __init__(self):
        self.read_sizes = []

    async def read(self, size=-1):
        self.read_sizes.append(size)
        return b"x" * (MAX_IMAGE_BYTES + 1)


def test_requires_server_api_key():
    try:
        run(validate_image_form("product", "商品场景", "1024x1024", None, None))
    except ImageRequestError as error:
        assert error.status_code == 500
        assert error.message == "服务器未配置 OPENAI_API_KEY。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_blank_server_api_key():
    try:
        run(validate_image_form("product", "商品场景", "1024x1024", None, "   "))
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


def test_rejects_removed_tool_ids():
    for tool_id in ("creator", "restore", "avatar"):
        try:
            run(validate_image_form(tool_id, "商品场景", "1024x1024", upload_file(), "key"))
        except ImageRequestError as error:
            assert error.status_code == 400
            assert error.message == "请选择有效的图片工具。"
        else:
            raise AssertionError("Expected ImageRequestError")


def test_rejects_product_image_generation_without_upload():
    try:
        run(
            validate_image_form(
                "product",
                "平台：拼多多\n画面比例：1:1",
                "2048x2048",
                None,
                "key",
                platform_style="pinduoduo",
                image_purpose="main-image",
                aspect_ratio="1:1",
                image_count="4",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请上传商品图。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_unsupported_file_types():
    try:
        run(
            validate_image_form(
                "product",
                "商品场景",
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


def test_rejects_mismatched_image_content():
    try:
        run(
            validate_image_form(
                "product",
                "商品场景",
                "1024x1024",
                upload_file(content_type="image/png", data=b"not an image"),
                "key",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "图片内容不是有效的 PNG、JPG 或 WebP。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_corrupt_image_content():
    try:
        run(
            validate_image_form(
                "product",
                "商品场景",
                "1024x1024",
                upload_file(content_type="image/png", data=BROKEN_PNG),
                "key",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "图片内容不是有效的 PNG、JPG 或 WebP。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_oversized_uploads():
    try:
        run(
            validate_image_form(
                "product",
                "商品场景",
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


def test_rejects_empty_submitted_product_image():
    try:
        run(
            validate_image_form(
                "product",
                "商品场景",
                "1024x1024",
                upload_file(data=b"", filename="empty.png"),
                "key",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "上传的图片为空。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_bounds_upload_reads_to_max_image_size_plus_one_byte():
    upload = RecordingUpload()

    try:
        run(validate_image_form("product", "商品场景", "1024x1024", upload, "key"))
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "图片不能超过 10MB。"
    else:
        raise AssertionError("Expected ImageRequestError")

    assert upload.read_sizes == [MAX_IMAGE_BYTES + 1]


def test_returns_normalized_valid_request():
    result = run(
        validate_image_form(
            "product",
            " 保持瓶身居中 ",
            "1536x1024",
            upload_file(content_type="image/png", filename="product.png"),
            "key",
        )
    )

    assert result.tool.id == "product"
    assert result.prompt == "保持瓶身居中"
    assert result.size == "1536x1024"
    assert result.image_bytes == TINY_PNG
    assert result.image_name == "product.png"
    assert result.image_type == "image/png"
    assert result.generation_settings == ProductGenerationSettings(
        aspect_ratio="",
        image_count=1,
    )


def test_falls_back_to_default_size_for_invalid_size_input():
    result = run(
        validate_image_form(
            "product",
            "商品场景",
            "800x800",
            upload_file(),
            "key",
        )
    )

    assert result.size == "1536x1024"


def test_accepts_gpt_image_2_popular_sizes():
    result = run(
        validate_image_form(
            "product",
            "横版直播封面",
            "3840x2160",
            upload_file(),
            "key",
            platform_style="douyin",
            image_purpose="promotion-image",
        )
    )

    assert result.size == "3840x2160"


def test_rejects_unsupported_aspect_ratio():
    try:
        run(
            validate_image_form(
                "product",
                "",
                "1536x1024",
                upload_file(),
                "key",
                platform_style="pinduoduo",
                image_purpose="main-image",
                aspect_ratio="4:5",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请选择有效的画面比例。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_rejects_unsupported_image_count():
    try:
        run(
            validate_image_form(
                "product",
                "",
                "1536x1024",
                upload_file(),
                "key",
                platform_style="pinduoduo",
                image_purpose="main-image",
                image_count="3",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "生成数量仅支持 1、2 或 4 张。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_compose_tool_prompt_combines_base_prompt_with_user_instructions():
    tool = get_tool_by_id("product")
    prompt = compose_tool_prompt(tool, "放在现代厨房里")

    assert tool.base_prompt in prompt
    assert "User request:" in prompt
    assert "放在现代厨房里" in prompt


def test_compose_tool_prompt_uses_base_prompt_when_optional_prompt_empty():
    tool = get_tool_by_id("product")

    assert compose_tool_prompt(tool, "   ") == tool.base_prompt


def test_documents_supported_upload_types():
    assert SUPPORTED_IMAGE_TYPES == ("image/png", "image/jpeg", "image/webp")


def test_product_request_normalizes_structured_fields():
    result = run(
        validate_image_form(
            "product",
            "  保持瓶身居中  ",
            "1536x1024",
            upload_file(content_type="image/png", filename="product.png"),
            "key",
            platform_style="pinduoduo",
            image_purpose="promotion-image",
            product_category="  小家电  ",
            selling_points="  三档风力，静音，USB 充电  ",
            scene_style="夏季桌面",
            visual_tone="高转化促销",
            promotion_text="限时立减 20 元",
            preserve_requirements="保留品牌 logo",
            avoid_elements="不要额外配件",
            aspect_ratio="2:3",
            image_count="2",
        )
    )

    assert result.tool.id == "product"
    assert result.prompt == "保持瓶身居中"
    assert result.product_fields == ProductImageFields(
        platform_style="pinduoduo",
        image_purpose="promotion-image",
        product_category="小家电",
        selling_points="三档风力，静音，USB 充电",
        scene_style="夏季桌面",
        visual_tone="高转化促销",
        promotion_text="限时立减 20 元",
        preserve_requirements="保留品牌 logo",
        avoid_elements="不要额外配件",
    )
    assert result.generation_settings == ProductGenerationSettings(
        aspect_ratio="2:3",
        image_count=2,
    )


def test_product_request_allows_legacy_prompt_without_structured_fields():
    result = run(
        validate_image_form(
            "product",
            "放在现代厨房里",
            "1536x1024",
            upload_file(content_type="image/png", filename="product.png"),
            "key",
        )
    )

    assert result.tool.id == "product"
    assert result.prompt == "放在现代厨房里"
    assert result.product_fields is None


def test_product_request_rejects_invalid_platform_style():
    try:
        run(
            validate_image_form(
                "product",
                "",
                "1536x1024",
                upload_file(),
                "key",
                platform_style="missing",
                image_purpose="main-image",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请选择有效的平台风格。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_product_request_rejects_invalid_image_purpose():
    try:
        run(
            validate_image_form(
                "product",
                "",
                "1536x1024",
                upload_file(),
                "key",
                platform_style="pinduoduo",
                image_purpose="missing",
            )
        )
    except ImageRequestError as error:
        assert error.status_code == 400
        assert error.message == "请选择有效的图片用途。"
    else:
        raise AssertionError("Expected ImageRequestError")


def test_compose_product_prompt_uses_structured_ecommerce_fields():
    tool = get_tool_by_id("product")
    prompt = compose_tool_prompt(
        tool,
        "保留瓶身居中",
        ProductImageFields(
            platform_style="pinduoduo",
            image_purpose="promotion-image",
            product_category="小家电",
            selling_points="三档风力，静音，USB 充电",
            scene_style="夏季桌面",
            visual_tone="高转化促销",
            promotion_text="限时立减 20 元",
            preserve_requirements="保留品牌 logo",
            avoid_elements="不要额外配件",
        ),
    )

    assert tool.base_prompt in prompt
    assert "Product preservation rules:" in prompt
    assert "Platform style (拼多多):" in prompt
    assert "high-conversion Pinduoduo" in prompt
    assert "Image purpose (促销图):" in prompt
    assert "Product category: 小家电" in prompt
    assert "Selling points: 三档风力，静音，USB 充电" in prompt
    assert "Promotion text: 限时立减 20 元" in prompt
    assert "Avoid elements: 不要额外配件" in prompt
    assert "Additional notes: 保留瓶身居中" in prompt
