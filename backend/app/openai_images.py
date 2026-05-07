from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable

from openai import OpenAI

from app.image_request import ValidImageRequest, compose_tool_prompt


@dataclass(frozen=True)
class GeneratedImageResult:
    src: str
    mime_type: str = "image/png"
    revised_prompt: str | None = None


def request_image_from_openai(
    request: ValidImageRequest,
    api_key: str,
    model: str,
    client_factory: Callable[..., Any] = OpenAI,
) -> GeneratedImageResult:
    client = client_factory(api_key=api_key)
    prompt = compose_tool_prompt(request.tool, request.prompt)

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
