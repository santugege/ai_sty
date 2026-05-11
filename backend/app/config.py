from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_KEYS = [
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_API_BASE",
    "OPENAI_API_BASE_URL",
    "OPENAI_IMAGE_MODEL",
    "OPENAI_AGENT_MODEL",
]


def load_backend_env(root: Path | None = None) -> None:
    backend_dir = root or Path(__file__).resolve().parents[1]
    _clear_empty_env_values(ENV_KEYS)
    load_dotenv(backend_dir / ".env", override=False)
    _clear_empty_env_values(ENV_KEYS)
    load_dotenv(backend_dir / ".env.example", override=False)


def _clear_empty_env_values(keys: list[str]) -> None:
    for key in keys:
        if os.environ.get(key) == "":
            os.environ.pop(key)


def openai_base_url() -> str | None:
    base_url = (
        os.getenv("OPENAI_BASE_URL")
        or os.getenv("OPENAI_API_BASE")
        or os.getenv("OPENAI_API_BASE_URL")
        or ""
    ).strip()
    return base_url or None


def openai_client_kwargs(api_key: str, base_url: str | None = None) -> dict[str, str]:
    kwargs = {"api_key": api_key}
    resolved_base_url = (base_url or "").strip()
    if resolved_base_url:
        kwargs["base_url"] = resolved_base_url
    return kwargs
