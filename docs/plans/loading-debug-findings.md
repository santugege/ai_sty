# Loading Debug Findings

## Initial Context

- `start.ps1` starts Docker services, migrations, FastAPI on `127.0.0.1:8000`, and Next.js on `127.0.0.1:3000`; it opens `http://localhost:3000`.
- Homepage renders `ProductWorkbench` behind `AuthProvider`.
- `AuthProvider` calls `getCurrentUser()` on mount, keeps `isLoading` true until that request settles, and redirects unauthenticated users to `/login`.
- High-probability root-cause paths: frontend auth API URL resolution, backend `/api/auth/me`, CORS/cookie behavior between `localhost` and `127.0.0.1`, or a backend startup/API failure.

## Evidence

- `.\start.ps1 -NoBrowser` completed successfully.
- `http://127.0.0.1:8000/health` returned `{"ok":true}`.
- `http://127.0.0.1:8000/api/auth/me` returned `{"user":null}` quickly.
- `Invoke-WebRequest http://localhost:3000` returned `200`.
- Listening sockets showed frontend bound to `127.0.0.1:3000` and backend bound to `127.0.0.1:8000`.
- Browser navigation to `http://localhost:3000` timed out before a usable page state was captured.

## Working Hypothesis

The page is not stuck because `/api/auth/me` is slow: browser traces show that request returns `200`. It is stuck because Next dev sends repeated Fast Refresh rebuilds every few hundred milliseconds, causing the document to reload before `AuthProvider` can finish its unauthenticated redirect.

The likely trigger is the current Next 16.2.5 Turbopack dev server in this repo. It writes generated files under `frontend/.next/dev`, while `next-env.d.ts` imports generated dev route types and `tsconfig.json` includes `.next/dev/types/**/*.ts`. This appears to create a self-refresh loop in the local dev runtime.

Secondary startup issues found:

- `start.ps1` opens `http://localhost:3000` while binding the frontend to `127.0.0.1`.
- `start.ps1` can start duplicate frontend/backend windows without checking whether the target ports are already occupied.
- `start.ps1` sleeps for 3 seconds before opening the browser instead of waiting for the frontend HTTP endpoint to become ready.
