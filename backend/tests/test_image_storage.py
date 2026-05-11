import app.image_storage as image_storage
from app.image_storage import extension_for_mime_type


def test_module_exposes_only_active_storage_backend():
    assert not hasattr(image_storage, "LocalImageStorage")
    assert not hasattr(image_storage, "decode_data_url")


def test_extension_for_mime_type_maps_supported_image_types():
    assert extension_for_mime_type("image/jpeg") == ".jpg"
    assert extension_for_mime_type("image/webp") == ".webp"
    assert extension_for_mime_type("image/png") == ".png"
