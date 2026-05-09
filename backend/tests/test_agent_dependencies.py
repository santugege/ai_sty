from pathlib import Path


def test_backend_dependencies_include_postgres_agent_stack():
    requirements = Path("backend/requirements.txt").read_text(encoding="utf-8")

    assert "sqlalchemy" in requirements
    assert "psycopg[binary]" in requirements
    assert "alembic" in requirements


def test_env_example_includes_agent_configuration():
    env_example = Path("backend/.env.example").read_text(encoding="utf-8")

    assert "DATABASE_URL=" in env_example
    assert "IMAGE_STORAGE_DIR=" in env_example
    assert "OPENAI_AGENT_MODEL=gpt-5.5" in env_example
    assert "OPENAI_IMAGE_MODEL=gpt-image-2" in env_example
