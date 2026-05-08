from __future__ import annotations

import base64
import binascii
import os
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DecodedImage:
    mime_type: str
    image_bytes: bytes


@dataclass(frozen=True)
class StoredImage:
    storage_key: str
    mime_type: str
    public_url: str | None = None


def decode_data_url(src: str) -> DecodedImage:
    if not src.startswith("data:") or ";base64," not in src:
        raise ValueError("Expected a base64 data URL image.")

    header, encoded = src.split(",", 1)
    mime_type = header.removeprefix("data:").removesuffix(";base64")
    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except binascii.Error as error:
        raise ValueError("Expected a base64 data URL image.") from error
    return DecodedImage(mime_type=mime_type, image_bytes=image_bytes)


def extension_for_mime_type(mime_type: str) -> str:
    if mime_type == "image/jpeg":
        return ".jpg"
    if mime_type == "image/webp":
        return ".webp"
    return ".png"


def _validate_storage_key(storage_key: str) -> str:
    path = Path(storage_key)
    if (
        path.name != storage_key
        or path.is_absolute()
        or "/" in storage_key
        or "\\" in storage_key
        or storage_key in {"", ".", ".."}
    ):
        raise ValueError("Expected a storage filename.")
    return storage_key


class LocalImageStorage:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or os.getenv("IMAGE_STORAGE_DIR", "backend/storage/images"))
        self.root.mkdir(parents=True, exist_ok=True)

    def write_image(self, image_bytes: bytes, mime_type: str = "image/png") -> StoredImage:
        storage_key = _validate_storage_key(f"{uuid.uuid4()}{extension_for_mime_type(mime_type)}")
        path = self.root / storage_key
        path.write_bytes(image_bytes)
        return StoredImage(storage_key=storage_key, mime_type=mime_type)

    def read_image(self, storage_key: str) -> bytes:
        return (self.root / _validate_storage_key(storage_key)).read_bytes()
