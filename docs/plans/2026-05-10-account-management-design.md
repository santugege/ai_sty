# Account Management Design

Date: 2026-05-10

## Goal

Add simple account management to the image toolbox. Users register with email, username, and password. The first registered account becomes the administrator. All app features require login except registration, login, logout, the current user endpoint, and health checks. Only the administrator can manage accounts.

## Decision

Use local database accounts with signed HTTP-only session cookies. Keep permissions deliberately small: a user is either the first administrator or a regular user. The product will not allow an administrator to promote other users to administrator.

This avoids JWT storage in the browser and avoids role or permission tables that the current product does not need.

## Data Model

Create a `users` table:

- `id uuid primary key`
- `user_id text unique not null`
- `email text unique not null`
- `username text unique not null`
- `password_hash text not null`
- `is_admin boolean not null default false`
- `is_active boolean not null default true`
- `created_at timestamptz not null`
- `updated_at timestamptz not null`

`user_id` is the stable business-facing user identifier. `id` remains the internal database key.

The first successful registration checks whether any user exists. If no user exists, the new account is created with `is_admin=true`; otherwise it is created with `is_admin=false`.

## Authentication

Use a backend-signed session cookie:

- Cookie name: `ai_sty_session`
- HTTP-only
- `SameSite=Lax`
- `Secure` enabled by environment in production
- Expiration configurable through `SESSION_TTL_HOURS`, defaulting to a reasonable app-session window

The session payload should include the user's internal `id` and enough metadata to validate expiration. Passwords are stored only as hashes, using a standard password hashing library such as bcrypt through `passlib[bcrypt]`.

If a user is inactive, login fails. If an already logged-in inactive user calls a protected API, the request returns `401`.

## API Design

Public routes:

```txt
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/me
GET /health
```

Protected routes:

```txt
GET /api/agent/sessions
POST /api/agent/sessions
GET /api/agent/sessions/{session_id}
POST /api/agent/sessions/{session_id}/messages
POST /api/images/generate
```

Administrator routes:

```txt
GET /api/admin/users
PATCH /api/admin/users/{user_id}
POST /api/admin/users/{user_id}/password
```

The admin list returns safe user fields only: `id`, `userId`, `email`, `username`, `isAdmin`, `isActive`, `createdAt`, and `updatedAt`.

The admin update route supports editing `email`, `username`, and `isActive`. It does not accept `isAdmin`.

The password route lets an administrator set a new password for a user. It does not return the password hash.

## Frontend Experience

Add three pages:

- `/login`
- `/register`
- `/admin/accounts`

The app shell should call `GET /api/auth/me` on load. If there is no active user, redirect to `/login`. The login page links to registration. After login or registration, redirect to the main product page.

The account management page is visible only to administrators. Regular users should not see the account navigation item, and direct visits to `/admin/accounts` should show an access-denied state or redirect after `/api/auth/me` confirms the user is not an administrator.

Keep the UI consistent with the existing compact workbench style: restrained panels, readable Chinese labels, concise validation errors, and no marketing-style landing page.

## Error Handling

Registration validates:

- valid email format
- non-empty username
- password length minimum
- unique email
- unique username

Login returns the same generic error for unknown email and wrong password.

Protected API requests without a valid session return `401`. Admin-only requests by regular users return `403`.

Administrators should not be able to deactivate their own account from the account management screen.

## Testing

Backend:

- model tests for `users` columns and uniqueness
- repository or service tests for first-user administrator creation
- password hashing and verification tests
- auth route tests for register, login, logout, and current user
- protected route tests requiring a session
- admin route tests for listing users, updating user fields, rejecting `isAdmin`, resetting passwords, and forbidding regular users

Frontend:

- auth API client tests
- route/source tests for login and registration forms
- account management source tests for admin-only controls and absence of admin promotion
- existing workbench tests updated for authenticated API calls where needed

Verification:

- `backend/.venv/Scripts/python -m pytest backend/tests -q`
- `npm test` in `frontend`
- `npm run lint` in `frontend`
- `npm run build` in `frontend`
