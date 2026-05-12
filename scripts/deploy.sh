#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is required." >&2
  exit 1
fi

if [[ ! -f .env.production ]]; then
  cp .env.production.example .env.production
  echo "Created .env.production from .env.production.example."
  echo "Edit .env.production and replace passwords, domains, OPENAI_API_KEY, and SESSION_SECRET, then rerun this script." >&2
  exit 1
fi

read_env_value() {
  local key="$1"
  awk -v key="$key" '
    index($0, key "=") == 1 {
      value = substr($0, length(key) + 2)
      sub(/\r$/, "", value)
      print value
      exit
    }
  ' .env.production
}

DATA_ROOT="$(read_env_value DATA_ROOT)"
DATA_ROOT="${DATA_ROOT:-/opt/ai_sty/data}"
mkdir -p "$DATA_ROOT/postgres" "$DATA_ROOT/minio"

POSTGRES_PASSWORD="$(read_env_value POSTGRES_PASSWORD)"
DATABASE_URL="$(read_env_value DATABASE_URL)"
APP_DOMAIN="$(read_env_value APP_DOMAIN)"
MINIO_ACCESS_KEY="$(read_env_value MINIO_ACCESS_KEY)"
MINIO_SECRET_KEY="$(read_env_value MINIO_SECRET_KEY)"
SESSION_SECRET="$(read_env_value SESSION_SECRET)"
OPENAI_API_KEY="$(read_env_value OPENAI_API_KEY)"

if [[ "${POSTGRES_PASSWORD:-}" == "change-this-postgres-password" ]]; then
  echo "Please change POSTGRES_PASSWORD in .env.production before deploying." >&2
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" || "${DATABASE_URL:-}" == *"change-this-postgres-password"* ]]; then
  echo "Please update DATABASE_URL in .env.production before deploying." >&2
  exit 1
fi

if [[ -z "${APP_DOMAIN:-}" ]]; then
  echo "Please set APP_DOMAIN in .env.production before deploying." >&2
  exit 1
fi

if [[ "${MINIO_ACCESS_KEY:-}" == "change-this-minio-user" || "${MINIO_SECRET_KEY:-}" == "change-this-minio-password" ]]; then
  echo "Please change MINIO_ACCESS_KEY and MINIO_SECRET_KEY in .env.production before deploying." >&2
  exit 1
fi

if [[ "${SESSION_SECRET:-}" == "change-this-long-random-session-secret" ]]; then
  echo "Please change SESSION_SECRET in .env.production before deploying." >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" || "${OPENAI_API_KEY:-}" == "change-this-openai-api-key" ]]; then
  echo "Please set OPENAI_API_KEY in .env.production before deploying." >&2
  exit 1
fi

docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.production -f docker-compose.prod.yml ps
