from pathlib import Path

import yaml
from dotenv import dotenv_values


def test_frontend_package_exposes_production_start_script():
    package_json = Path("frontend/package.json").read_text(encoding="utf-8")

    assert '"start": "next start -H 0.0.0.0"' in package_json


def test_production_compose_runs_full_stack_with_persistent_data():
    compose = yaml.safe_load(Path("docker-compose.prod.yml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"postgres", "minio", "minio-init", "backend", "frontend", "caddy"} <= set(services)

    postgres = services["postgres"]
    assert postgres["restart"] == "unless-stopped"
    assert postgres["environment"]["POSTGRES_USER"] == "${POSTGRES_USER:-postgres}"
    assert postgres["environment"]["POSTGRES_PASSWORD"] == "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
    assert postgres["environment"]["POSTGRES_DB"] == "${POSTGRES_DB:-image_agent}"
    assert "127.0.0.1:5432:5432" in postgres["ports"]
    assert "${DATA_ROOT:-/opt/ai_sty/data}/postgres:/var/lib/postgresql/data" in postgres[
        "volumes"
    ]
    assert "pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-image_agent}" in postgres[
        "healthcheck"
    ]["test"]

    minio = services["minio"]
    assert minio["restart"] == "unless-stopped"
    assert minio["environment"]["MINIO_ROOT_USER"] == "${MINIO_ACCESS_KEY:?MINIO_ACCESS_KEY is required}"
    assert minio["environment"]["MINIO_ROOT_PASSWORD"] == "${MINIO_SECRET_KEY:?MINIO_SECRET_KEY is required}"
    assert "127.0.0.1:9000:9000" in minio["ports"]
    assert "127.0.0.1:9001:9001" in minio["ports"]
    assert "${DATA_ROOT:-/opt/ai_sty/data}/minio:/data" in minio["volumes"]
    assert minio["healthcheck"]["test"] == ["CMD", "mc", "ready", "local"]

    backend = services["backend"]
    assert backend["build"]["context"] == "."
    assert backend["build"]["dockerfile"] == "backend/Dockerfile"
    assert backend["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert backend["depends_on"]["minio"]["condition"] == "service_healthy"
    assert backend["env_file"] == [".env.production"]
    assert (
        "python -m alembic -c backend/alembic.ini upgrade head && "
        "uvicorn app.main:app --host 0.0.0.0 --port 8000"
    ) in backend["command"]

    frontend = services["frontend"]
    assert frontend["build"]["context"] == "."
    assert frontend["build"]["dockerfile"] == "frontend/Dockerfile"
    assert frontend["build"]["args"]["NEXT_PUBLIC_API_BASE_URL"] == "${NEXT_PUBLIC_API_BASE_URL:?NEXT_PUBLIC_API_BASE_URL is required}"
    assert frontend["depends_on"]["backend"]["condition"] == "service_healthy"
    assert "127.0.0.1:3000:3000" in frontend["ports"]

    caddy = services["caddy"]
    assert caddy["image"] == "${CADDY_IMAGE:-m.daocloud.io/docker.io/library/caddy:2-alpine}"
    assert caddy["env_file"] == [".env.production"]
    assert "80:80" in caddy["ports"]
    assert "443:443" in caddy["ports"]
    assert "./deploy/Caddyfile:/etc/caddy/Caddyfile:ro" in caddy["volumes"]
    assert "${DATA_ROOT:-/opt/ai_sty/data}/caddy/data:/data" in caddy["volumes"]
    assert caddy["depends_on"]["frontend"]["condition"] == "service_healthy"
    assert caddy["depends_on"]["backend"]["condition"] == "service_healthy"

    minio_init = services["minio-init"]
    assert minio_init["depends_on"]["minio"]["condition"] == "service_healthy"
    assert "mc mb --ignore-existing local/$${MINIO_BUCKET:-agent-images}" in minio_init[
        "entrypoint"
    ]
    assert "mc anonymous set download local/$${MINIO_BUCKET:-agent-images}" in minio_init[
        "entrypoint"
    ]


def test_production_env_template_uses_container_network_and_disk_data_root():
    values = dotenv_values(".env.production.example")

    assert values["APP_DOMAIN"] == "nd.v3cu.com"
    assert values["DATA_ROOT"] == "/opt/ai_sty/data"
    assert values["DATABASE_URL"] == (
        "postgresql+psycopg://postgres:change-this-postgres-password@postgres:5432/image_agent"
    )
    assert values["MINIO_ENDPOINT"] == "http://minio:9000"
    assert values["MINIO_PUBLIC_ENDPOINT"] == "https://nd.v3cu.com"
    assert values["FRONTEND_ORIGIN"] == "https://nd.v3cu.com"
    assert values["BACKEND_PUBLIC_ORIGIN"] == "https://nd.v3cu.com"
    assert values["SESSION_COOKIE_SECURE"] == "true"
    assert values["NEXT_PUBLIC_API_BASE_URL"] == "https://nd.v3cu.com"


def test_production_dockerfiles_and_deploy_script_are_present():
    backend_dockerfile = Path("backend/Dockerfile").read_text(encoding="utf-8")
    frontend_dockerfile = Path("frontend/Dockerfile").read_text(encoding="utf-8")
    deploy_script = Path("scripts/deploy.sh").read_text(encoding="utf-8")

    assert "pip install --no-cache-dir -r backend/requirements.txt" in backend_dockerfile
    assert 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]' in backend_dockerfile
    assert "ARG NEXT_PUBLIC_API_BASE_URL" in frontend_dockerfile
    assert frontend_dockerfile.index("RUN npm ci") < frontend_dockerfile.index(
        "ENV NODE_ENV=production"
    )
    assert "RUN npm run build" in frontend_dockerfile
    assert 'CMD ["npm", "run", "start"]' in frontend_dockerfile
    assert "docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build" in deploy_script
    assert "mkdir -p \"$DATA_ROOT/postgres\" \"$DATA_ROOT/minio\"" in deploy_script
    assert "cp .env.production.example .env.production" in deploy_script
    assert "read_env_value()" in deploy_script
    assert "source .env.production" not in deploy_script
    assert "Please update DATABASE_URL in .env.production before deploying." in deploy_script
    assert "Please set APP_DOMAIN in .env.production before deploying." in deploy_script


def test_caddyfile_routes_domain_to_app_api_and_minio():
    caddyfile = Path("deploy/Caddyfile").read_text(encoding="utf-8")

    assert "{$APP_DOMAIN}" in caddyfile
    assert "reverse_proxy frontend:3000" in caddyfile
    assert "handle /api/*" in caddyfile
    assert "reverse_proxy backend:8000" in caddyfile
    assert "handle /agent-images/*" in caddyfile
    assert "reverse_proxy minio:9000" in caddyfile
