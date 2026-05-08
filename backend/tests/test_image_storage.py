import base64

import pytest

from app.image_storage import LocalImageStorage, decode_data_url, extension_for_mime_type


def test_decode_data_url_returns_mime_type_and_bytes():
    encoded = base64.b64encode(b"image").decode("ascii")

    decoded = decode_data_url(f"data:image/png;base64,{encoded}")

    assert decoded.mime_type == "image/png"
    assert decoded.image_bytes == b"image"


def test_decode_data_url_rejects_malformed_base64():
    with pytest.raises(ValueError, match="Expected a base64 data URL image."):
        decode_data_url("data:image/png;base64,!!!!")


def test_extension_for_mime_type_maps_supported_image_types():
    assert extension_for_mime_type("image/jpeg") == ".jpg"
    assert extension_for_mime_type("image/webp") == ".webp"
    assert extension_for_mime_type("image/png") == ".png"


def test_local_image_storage_writes_and_reads_image(tmp_path):
    storage = LocalImageStorage(tmp_path)

    stored = storage.write_image(b"image", mime_type="image/png")

    assert stored.storage_key.endswith(".png")
    assert "/" not in stored.storage_key
    assert "\\" not in stored.storage_key
    assert stored.mime_type == "image/png"
    assert (tmp_path / stored.storage_key).read_bytes() == b"image"
    assert storage.read_image(stored.storage_key) == b"image"


def test_local_image_storage_rejects_path_traversal(tmp_path):
    storage = LocalImageStorage(tmp_path)

    with pytest.raises(ValueError, match="Expected a storage filename."):
        storage.read_image("../image.png")


def test_local_image_storage_rejects_absolute_path(tmp_path):
    storage = LocalImageStorage(tmp_path)

    with pytest.raises(ValueError, match="Expected a storage filename."):
        storage.read_image(str(tmp_path / "image.png"))


def test_local_image_storage_rejects_windows_style_separator(tmp_path):
    storage = LocalImageStorage(tmp_path)

    with pytest.raises(ValueError, match="Expected a storage filename."):
        storage.read_image("..\\image.png")
