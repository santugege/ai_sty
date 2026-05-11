# ZPAY Integration Task Plan

## Goal

Integrate ZPAY payments with the existing FastAPI backend and Next.js frontend without adding the alpha PyPI SDK dependency.

## Decisions

- Implement a small internal backend client for ZPAY signing, payment URL creation, query parsing, and callback verification.
- Keep payment state in the backend database so callbacks are idempotent and auditable.
- Expose only backend-owned payment routes to the frontend.

## Phases

- [x] Inspect project stack and existing route/test patterns.
- [x] Add ZPAY client tests and implementation.
- [x] Add payment models, repository/service, routes, and tests.
- [x] Add frontend API helper and payment page/entry.
- [x] Run backend and frontend verification.
