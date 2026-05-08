from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Protocol


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
