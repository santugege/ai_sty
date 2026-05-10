from pathlib import Path
from urllib.parse import urlsplit

import yaml
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
    assert "pyyaml" in requirements.lower()


def test_docker_compose_defines_postgres_and_minio():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    env_values = dotenv_values("backend/.env.example")
    database = urlsplit(env_values["DATABASE_URL"])

    services = compose["services"]
    postgres = services["postgres"]
    minio = services["minio"]
    minio_init = services["minio-init"]

    assert postgres["image"] == "postgres:16"
    assert postgres["container_name"] == "ai_sty_postgres"
    assert postgres["restart"] == "unless-stopped"
    assert postgres["environment"] == {
        "POSTGRES_USER": database.username,
        "POSTGRES_PASSWORD": database.password,
        "POSTGRES_DB": database.path.lstrip("/"),
    }
    assert f"{database.port}:{database.port}" in postgres["ports"]
    assert "postgres_data:/var/lib/postgresql/data" in postgres["volumes"]
    assert "pg_isready -U postgres -d image_agent" in postgres["healthcheck"]["test"]

    minio_endpoint = urlsplit(env_values["MINIO_ENDPOINT"])
    minio_port = minio_endpoint.port
    assert minio["image"] == "minio/minio:latest"
    assert minio["container_name"] == "ai_sty_minio"
    assert minio["restart"] == "unless-stopped"
    assert minio["command"] == 'server /data --console-address ":9001"'
    assert minio["environment"] == {
        "MINIO_ROOT_USER": env_values["MINIO_ACCESS_KEY"],
        "MINIO_ROOT_PASSWORD": env_values["MINIO_SECRET_KEY"],
    }
    assert f"{minio_port}:{minio_port}" in minio["ports"]
    assert "9001:9001" in minio["ports"]
    assert "minio_data:/data" in minio["volumes"]
    assert minio["healthcheck"]["test"] == ["CMD", "mc", "ready", "local"]

    assert minio_init["image"] == "minio/mc:latest"
    assert minio_init["depends_on"]["minio"]["condition"] == "service_healthy"
    assert (
        f"mc alias set local http://minio:{minio_port} "
        f"{env_values['MINIO_ACCESS_KEY']} {env_values['MINIO_SECRET_KEY']}"
    ) in minio_init["entrypoint"]
    assert f"mc mb --ignore-existing local/{env_values['MINIO_BUCKET']}" in minio_init["entrypoint"]
    assert {"postgres_data", "minio_data"} <= set(compose["volumes"])
