from pathlib import Path

from dotenv import dotenv_values


def test_backend_dependencies_include_postgres_agent_stack():
    requirements = Path("backend/requirements.txt").read_text(encoding="utf-8")

    assert "sqlalchemy" in requirements
    assert "psycopg[binary]" in requirements
    assert "alembic" in requirements


def test_env_example_includes_agent_configuration():
    env_example = Path("backend/.env.example").read_text(encoding="utf-8")
    values = dotenv_values("backend/.env.example")

    assert "DATABASE_URL=" in env_example
    assert "IMAGE_STORAGE_DIR=" in env_example
    assert values.get("OPENAI_AGENT_MODEL")
    assert values.get("OPENAI_IMAGE_MODEL")
