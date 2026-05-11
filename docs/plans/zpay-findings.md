# ZPAY Integration Findings

## Project Context

- Backend: FastAPI, SQLAlchemy, Alembic, pytest, httpx.
- Frontend: Next.js App Router, React, TypeScript, Tailwind CSS.
- Authentication uses a session cookie and backend dependencies in `backend/app/auth_dependencies.py`.
- There is no existing payment module.

## ZPAY Context

- The compatible ZPAY API uses MD5 signing over sorted non-empty parameters plus merchant key.
- Public docs describe submit URL payments, API payments, order query/refund endpoints, async notify callbacks, and sync return callbacks.
- A PyPI package named `zpay` exists, but the current release requires Python >=3.12. This project uses Python 3.11.9.

