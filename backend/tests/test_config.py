from pathlib import Path

from app.config import load_backend_env, openai_base_url, openai_client_kwargs


def test_load_backend_env_reads_env_example(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    (tmp_path / ".env.example").write_text(
        "OPENAI_API_KEY=from-example\nOPENAI_BASE_URL=https://api.example.test/v1\n",
        encoding="utf-8",
    )

    load_backend_env(tmp_path)

    assert openai_base_url() == "https://api.example.test/v1"
    assert openai_client_kwargs("from-example", openai_base_url()) == {
        "api_key": "from-example",
        "base_url": "https://api.example.test/v1",
    }


def test_load_backend_env_keeps_process_env_over_env_example(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("OPENAI_API_KEY", "from-process")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://process.example.test/v1")
    (tmp_path / ".env.example").write_text(
        "OPENAI_API_KEY=from-example\nOPENAI_BASE_URL=https://file.example.test/v1\n",
        encoding="utf-8",
    )

    load_backend_env(tmp_path)

    assert openai_base_url() == "https://process.example.test/v1"
    assert openai_client_kwargs("from-process", openai_base_url()) == {
        "api_key": "from-process",
        "base_url": "https://process.example.test/v1",
    }


def test_load_backend_env_uses_env_example_when_process_env_is_empty(
    monkeypatch, tmp_path: Path
):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    (tmp_path / ".env.example").write_text(
        "OPENAI_API_KEY=from-example\nOPENAI_BASE_URL=https://api.example.test/v1\n",
        encoding="utf-8",
    )

    load_backend_env(tmp_path)

    assert openai_client_kwargs("from-example", openai_base_url()) == {
        "api_key": "from-example",
        "base_url": "https://api.example.test/v1",
    }
