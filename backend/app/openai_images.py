from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable

from openai import OpenAI

from app.config import openai_client_kwargs
from app.image_request import ValidImageRequest, compose_tool_prompt


@dataclass(frozen=True)
class GeneratedImageResult:
    src: str
    mime_type: str = "image/png"
    revised_prompt: str | None = None


@dataclass(frozen=True)
class GeneratedImageEnvelope:
    images: list[GeneratedImageResult]

    @classmethod
    def from_images(
        cls,
        images: list[GeneratedImageResult],
    ) -> "GeneratedImageEnvelope":
        return cls(images=images)

    @property
    def src(self) -> str:
        return self.first.src

    @property
    def mime_type(self) -> str:
        return self.first.mime_type

    @property
    def revised_prompt(self) -> str | None:
        return self.first.revised_prompt

    @property
    def first(self) -> GeneratedImageResult:
        if not self.images:
            raise RuntimeError("OpenAI 没有返回图片结果。")
        return self.images[0]


def request_image_from_openai(
    request: ValidImageRequest,
    api_key: str,
    model: str,
    base_url: str | None = None,
    client_factory: Callable[..., Any] = OpenAI,
) -> GeneratedImageEnvelope:
    client = client_factory(**openai_client_kwargs(api_key, base_url))
    prompt = compose_tool_prompt(
        request.tool,
        request.prompt,
        request.product_fields,
        request.generation_settings,
    )

    images = [
        request_single_image(client, request, model, prompt)
        for _ in range(request.generation_settings.image_count)
    ]
    return GeneratedImageEnvelope.from_images(images)


def request_single_image(
    client: Any,
    request: ValidImageRequest,
    model: str,
    prompt: str,
) -> GeneratedImageResult:
    if request.image_bytes:
        image_file = BytesIO(request.image_bytes)
        image_file.name = request.image_name or "input.png"
        response = client.images.edit(
            model=model,
            image=image_file,
            prompt=prompt,
            size=request.size,
            quality="auto",
        )
        return normalize_openai_image_response(response)

    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=request.size,
        quality="auto",
    )
    return normalize_openai_image_response(response)


def normalize_openai_image_response(response: Any) -> GeneratedImageResult:
    data = _read(response, "data") or []
    image = data[0] if data else None

    if image is None:
        raise RuntimeError("OpenAI 没有返回图片结果。")

    b64_json = _read(image, "b64_json")
    revised_prompt = _read(image, "revised_prompt")

    if b64_json:
        return GeneratedImageResult(
            src=f"data:image/png;base64,{b64_json}",
            revised_prompt=revised_prompt,
        )

    url = _read(image, "url")
    if url:
        return GeneratedImageResult(src=url, revised_prompt=revised_prompt)

    raise RuntimeError("OpenAI 没有返回图片结果。")


def _read(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
