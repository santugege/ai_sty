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
  images?: ConversationImage[];
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

export type AgentStreamEvent = {
  event: string;
  data: Record<string, unknown>;
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

export async function streamAgentSession(
  formData: FormData,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
) {
  return readAgentStream(
    await fetch(`${apiBaseUrl}/api/agent/sessions/stream`, {
      method: "POST",
      credentials: "include",
      body: formData,
      signal,
    }),
    onEvent,
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

export async function streamAgentSessionMessage(
  sessionId: string,
  formData: FormData,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
) {
  const encodedSessionId = encodeURIComponent(sessionId);
  return readAgentStream(
    await fetch(
      `${apiBaseUrl}/api/agent/sessions/${encodedSessionId}/messages/stream`,
      {
        method: "POST",
        credentials: "include",
        body: formData,
        signal,
      },
    ),
    onEvent,
  );
}

async function readAgentResponse(response: Response): Promise<AgentEnvelope> {
  return readJsonResponse<AgentEnvelope>(response);
}

async function readAgentStream(
  response: Response,
  onEvent: (event: AgentStreamEvent) => void,
) {
  if (!response.ok || !response.body) {
    await readJsonResponse(response);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const parsed = parseServerSentEvent(frame);
      if (parsed) {
        onEvent(parsed);
      }
    }
    if (done) {
      break;
    }
  }

  const trailing = parseServerSentEvent(buffer);
  if (trailing) {
    onEvent(trailing);
  }
}

function parseServerSentEvent(frame: string): AgentStreamEvent | null {
  const lines = frame.split(/\r?\n/);
  const event = lines
    .find((line) => line.startsWith("event:"))
    ?.slice("event:".length)
    .trim();
  const data = lines
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice("data:".length).trimStart())
    .join("\n");

  if (!event || !data) {
    return null;
  }

  const payload = JSON.parse(data) as Record<string, unknown>;
  if (event === "error") {
    throw new Error(String(payload.error || "Agent request failed."));
  }
  return { event, data: payload };
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
