const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type CurrentUser = {
  id: string;
  userId: string;
  email: string;
  username: string;
  isAdmin: boolean;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
};

export type AuthEnvelope = {
  user: CurrentUser | null;
};

export type UserListEnvelope = {
  users: CurrentUser[];
};

export type RegisterAccountInput = {
  email: string;
  username: string;
  password: string;
};

export type LoginAccountInput = {
  email: string;
  password: string;
};

export type UpdateUserInput = {
  email?: string;
  username?: string;
  isActive?: boolean;
};

export async function getCurrentUser(): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/auth/me`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function registerAccount(
  input: RegisterAccountInput,
): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function loginAccount(input: LoginAccountInput): Promise<AuthEnvelope> {
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function logoutAccount() {
  return readJsonResponse<{ ok: boolean }>(
    await fetch(`${apiBaseUrl}/api/auth/logout`, {
      method: "POST",
      credentials: "include",
    }),
  );
}

export async function listUsers(): Promise<UserListEnvelope> {
  return readJsonResponse<UserListEnvelope>(
    await fetch(`${apiBaseUrl}/api/admin/users`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function updateUser(
  userId: string,
  updates: UpdateUserInput,
): Promise<AuthEnvelope> {
  const encodedUserId = encodeURIComponent(userId);
  const body: UpdateUserInput = {
    email: updates.email,
    username: updates.username,
    isActive: updates.isActive,
  };

  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/admin/users/${encodedUserId}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
  );
}

export async function resetUserPassword(
  userId: string,
  password: string,
): Promise<AuthEnvelope> {
  const encodedUserId = encodeURIComponent(userId);
  return readJsonResponse<AuthEnvelope>(
    await fetch(`${apiBaseUrl}/api/admin/users/${encodedUserId}/password`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
    }),
  );
}

async function readJsonResponse<T>(response: Response): Promise<T> {
  const payload = await readJsonPayload<T>(response);
  if (!response.ok || payload.error || payload.detail) {
    throw new Error(payload.error || payload.detail || "Auth request failed.");
  }
  return payload;
}

async function readJsonPayload<T>(
  response: Response,
): Promise<T & { error?: string | null; detail?: string | null }> {
  const contentType = response.headers.get("content-type")?.toLowerCase();

  if (!contentType?.includes("json")) {
    return {} as T & { error?: string | null; detail?: string | null };
  }

  try {
    return (await response.json()) as T & {
      error?: string | null;
      detail?: string | null;
    };
  } catch {
    return {} as T & { error?: string | null; detail?: string | null };
  }
}
