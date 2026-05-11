const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type ConversationAttachment = {
  id: string;
  name: string;
  mimeType: string;
  src: string;
  createdAt: string;
};

export type ConversationImage = {
  id: string;
  src: string;
  mimeType: string;
  prompt: string;
  revisedPrompt?: string | null;
  model: string;
  createdAt: string;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  attachments: ConversationAttachment[];
  responseId?: string | null;
  imageVersionId?: string | null;
  image?: ConversationImage | null;
  createdAt: string;
};

export type ConversationListItem = {
  id: string;
  title: string;
  summary?: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type ConversationListEnvelope = {
  sessions: ConversationListItem[];
};

export type AgentEnvelope = {
  conversation: {
    id: string;
    title: string;
    summary?: string | null;
    previousResponseId?: string | null;
    status: string;
    createdAt: string;
    updatedAt: string;
  };
  messages: ConversationMessage[];
  error?: string | null;
};

export async function listAgentSessions(): Promise<ConversationListEnvelope> {
  return readJsonResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function createAgentSession(formData: FormData) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions`, {
      method: "POST",
      credentials: "include",
      body: formData,
    }),
  );
}

export async function getAgentSession(sessionId: string) {
  const encodedSessionId = encodeURIComponent(sessionId);
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions/${encodedSessionId}`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function sendAgentSessionMessage(
  sessionId: string,
  formData: FormData,
) {
  const encodedSessionId = encodeURIComponent(sessionId);
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions/${encodedSessionId}/messages`, {
      method: "POST",
      credentials: "include",
      body: formData,
    }),
  );
}

async function readAgentResponse(response: Response): Promise<AgentEnvelope> {
  return readJsonResponse<AgentEnvelope>(response);
}

async function readJsonResponse<T>(response: Response): Promise<T> {
  const payload = await readJsonPayload<T>(response);
  if (!response.ok || payload.error || payload.detail) {
    throw new Error(payload.error || payload.detail || "Agent request failed.");
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
