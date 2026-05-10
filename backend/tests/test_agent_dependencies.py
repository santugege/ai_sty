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
    assert values.get("OPENAI_AGENT_MODEL")
    assert values.get("OPENAI_IMAGE_MODEL")


def test_backend_dependencies_include_minio_storage_stack():
    requirements = Path("backend/requirements.txt").read_text(encoding="utf-8")
    env_example = Path("backend/.env.example").read_text(encoding="utf-8")

    assert "boto3" in requirements
    assert "MINIO_ENDPOINT=" in env_example
    assert "MINIO_BUCKET=" in env_example
    assert "MINIO_ACCESS_KEY=" in env_example
    assert "MINIO_SECRET_KEY=" in env_example
