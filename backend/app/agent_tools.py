from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable, Protocol

from openai import OpenAI

from app.config import openai_client_kwargs

DEFAULT_AGENT_IMAGE_QUALITY = "auto"
SUPPORTED_AGENT_IMAGE_QUALITIES = ("auto", "low", "medium", "high")


@dataclass(frozen=True)
class AgentToolContext:
    image_bytes: bytes
    image_name: str
    mime_type: str
    instruction: str
    size: str
    quality: str = DEFAULT_AGENT_IMAGE_QUALITY


@dataclass(frozen=True)
class AgentToolResult:
    image_bytes: bytes
    mime_type: str
    prompt: str
    revised_prompt: str | None
    model: str


class AgentTool(Protocol):
    name: str
    description: str

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        ...


class ImageClient(Protocol):
    def generate(self, instruction: str, size: str, quality: str) -> bytes:
        ...

    def edit(self, context: AgentToolContext) -> bytes:
        ...


class AgentToolRegistry:
    def __init__(self, tools: list[AgentTool]):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)


@dataclass(frozen=True)
class OpenAIImageClient:
    api_key: str
    image_model: str
    base_url: str | None = None
    client_factory: Callable[..., Any] = OpenAI

    def generate(
        self,
        instruction: str,
        size: str,
        quality: str = DEFAULT_AGENT_IMAGE_QUALITY,
    ) -> bytes:
        client = self.client_factory(**openai_client_kwargs(self.api_key, self.base_url))
        response = client.images.generate(
            model=self.image_model,
            prompt=instruction,
            size=size,
            quality=normalize_agent_image_quality(quality),
        )
        return _decode_first_image(response)

    def edit(self, context: AgentToolContext) -> bytes:
        client = self.client_factory(**openai_client_kwargs(self.api_key, self.base_url))
        image_file = BytesIO(context.image_bytes)
        image_file.name = context.image_name
        response = client.images.edit(
            model=self.image_model,
            image=image_file,
            prompt=context.instruction,
            size=context.size,
            quality=normalize_agent_image_quality(context.quality),
        )
        return _decode_first_image(response)


class ChatGptImageGenerateTool:
    name = "chatgpt_image_generate"
    description = "Generate a new image from a ChatGPT general image prompt."

    def __init__(
        self,
        image_client: ImageClient,
        image_model: str | None = None,
    ):
        self._image_client = image_client
        self.image_model = image_model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        image_bytes = self._image_client.generate(
            context.instruction,
            context.size,
            context.quality,
        )
        return AgentToolResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt=None,
            model=self.image_model,
        )


class ChatGptImageEditTool:
    name = "chatgpt_image_edit"
    description = "Edit the current image using a ChatGPT general image prompt."

    def __init__(
        self,
        image_client: ImageClient,
        image_model: str | None = None,
    ):
        self._image_client = image_client
        self.image_model = image_model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        image_bytes = self._image_client.edit(context)
        return AgentToolResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt=None,
            model=self.image_model,
        )


def create_openai_image_client(
    api_key: str,
    image_model: str,
    base_url: str | None = None,
    client_factory: Callable[..., Any] = OpenAI,
) -> OpenAIImageClient:
    return OpenAIImageClient(
        api_key=api_key,
        image_model=image_model,
        base_url=base_url,
        client_factory=client_factory,
    )


def normalize_agent_image_quality(quality: str | None) -> str:
    normalized = (quality or "").strip().lower()
    if normalized in SUPPORTED_AGENT_IMAGE_QUALITIES:
        return normalized
    return DEFAULT_AGENT_IMAGE_QUALITY


def _decode_first_image(response: Any) -> bytes:
    data = _read(response, "data") or []
    first_image = data[0] if data else None
    b64_json = _read(first_image, "b64_json") if first_image is not None else None
    if not b64_json:
        raise RuntimeError("OpenAI did not return image data.")

    try:
        return base64.b64decode(b64_json, validate=True)
    except (binascii.Error, ValueError) as error:
        raise RuntimeError("OpenAI returned invalid base64 image data.") from error


def _read(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
