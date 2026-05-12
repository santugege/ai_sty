# Production Deployment

This project can run as a Docker Compose stack with PostgreSQL, MinIO, the FastAPI backend, the Next.js frontend, and Caddy for HTTPS.

The production domain is `https://nd.v3cu.com`.

## First Deploy

1. Install Docker and Docker Compose on the server.
2. Copy or pull this repository onto the server.
3. Run:

```bash
bash scripts/deploy.sh
```

The first run creates `.env.production` and stops. Edit that file before running the script again.

Required changes:

- `POSTGRES_PASSWORD`
- `DATABASE_URL` with the same PostgreSQL password
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `OPENAI_API_KEY`
- `SESSION_SECRET`
- public origins such as `FRONTEND_ORIGIN`, `BACKEND_PUBLIC_ORIGIN`, `NEXT_PUBLIC_API_BASE_URL`, and `MINIO_PUBLIC_ENDPOINT` if the domain changes

For `nd.v3cu.com`, the generated production values should use:

```env
APP_DOMAIN=nd.v3cu.com
FRONTEND_ORIGIN=https://nd.v3cu.com
BACKEND_PUBLIC_ORIGIN=https://nd.v3cu.com
NEXT_PUBLIC_API_BASE_URL=https://nd.v3cu.com
MINIO_PUBLIC_ENDPOINT=https://nd.v3cu.com
SESSION_COOKIE_SECURE=true
```

Run again after editing:

```bash
bash scripts/deploy.sh
```

## Persistent Data

PostgreSQL and MinIO data are stored on the host under `DATA_ROOT`.

Default paths:

- `/opt/ai_sty/data/postgres`
- `/opt/ai_sty/data/minio`

Changing `DATA_ROOT` in `.env.production` moves where future deployments mount data.

## Ports

Default exposed services:

- Public app: `https://nd.v3cu.com`
- Backend API through Caddy: `https://nd.v3cu.com/api/*`
- MinIO image URLs through Caddy: `https://nd.v3cu.com/agent-images/*`

Public ports:

- HTTP: `80`
- HTTPS: `443`

Internal/admin ports bind to `127.0.0.1` by default:

- PostgreSQL: `127.0.0.1:5432`
- Frontend direct port: `127.0.0.1:3000`
- MinIO API direct port: `127.0.0.1:9000`
- MinIO console: `127.0.0.1:9001`

Use an SSH tunnel or a reverse proxy if you need remote admin access.

Before starting Caddy, make sure DNS for `nd.v3cu.com` points to this server and that ports `80` and `443` are reachable. Caddy will request and renew HTTPS certificates automatically.

## Operations

View status:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
```

View logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend frontend
```

Update after pulling new code:

```bash
bash scripts/deploy.sh
```

Stop services without deleting data:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```
