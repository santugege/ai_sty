from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable, Protocol

from openai import OpenAI


@dataclass(frozen=True)
class AgentToolContext:
    image_bytes: bytes
    image_name: str
    mime_type: str
    instruction: str
    size: str


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


class AgentToolRegistry:
    def __init__(self, tools: list[AgentTool]):
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)


class GptImage2EditTool:
    name = "gpt_image_2_edit"
    description = "Edit the current product image using gpt-image-2."

    def __init__(
        self,
        image_client: Callable[[AgentToolContext], bytes],
        image_model: str | None = None,
    ):
        self._image_client = image_client
        self.image_model = image_model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        image_bytes = self._image_client(context)
        return AgentToolResult(
            image_bytes=image_bytes,
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt=None,
            model=self.image_model,
        )


def _read(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def create_openai_image_client(
    api_key: str,
    image_model: str,
    client_factory: Callable[..., Any] = OpenAI,
) -> Callable[[AgentToolContext], bytes]:
    def edit_image(context: AgentToolContext) -> bytes:
        client = client_factory(api_key=api_key)
        image_file = BytesIO(context.image_bytes)
        image_file.name = context.image_name
        response = client.images.edit(
            model=image_model,
            image=image_file,
            prompt=context.instruction,
            size=context.size,
            quality="auto",
        )
        data = _read(response, "data") or []
        first_image = data[0] if data else None
        b64_json = _read(first_image, "b64_json") if first_image is not None else None
        if not b64_json:
            raise RuntimeError("OpenAI did not return image data.")

        try:
            return base64.b64decode(b64_json, validate=True)
        except (binascii.Error, ValueError) as error:
            raise RuntimeError("OpenAI returned invalid base64 image data.") from error

    return edit_image
