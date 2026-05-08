const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type AgentMessage = {
  id: string;
  sessionId: string;
  role: "user" | "assistant" | "tool";
  content: string;
  responseId?: string | null;
  toolCallId?: string | null;
  createdAt: string;
};

export type AgentImageVersion = {
  id: string;
  sessionId: string;
  parentVersionId?: string | null;
  src: string;
  storageKey: string;
  mimeType: string;
  width?: number | null;
  height?: number | null;
  prompt: string;
  revisedPrompt?: string | null;
  model: string;
  createdAt: string;
};

export type AgentEnvelope = {
  session: {
    id: string;
    title: string;
    currentVersionId?: string | null;
    previousResponseId?: string | null;
    status: string;
    createdAt: string;
    updatedAt: string;
  };
  messages: AgentMessage[];
  currentImage?: AgentImageVersion | null;
  versions: AgentImageVersion[];
  pendingQuestion?: string | null;
  error?: string | null;
};

export async function createAgentSession(formData: FormData) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions`, {
      method: "POST",
      body: formData,
    }),
  );
}

export async function sendAgentMessage(
  sessionId: string,
  instruction: string,
  size: string,
) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ instruction, size }),
    }),
  );
}

export async function restoreAgentVersion(sessionId: string, versionId: string) {
  return readAgentResponse(
    await fetch(
      `${apiBaseUrl}/api/agent/sessions/${sessionId}/versions/${versionId}/restore`,
      {
        method: "POST",
      },
    ),
  );
}

async function readAgentResponse(response: Response): Promise<AgentEnvelope> {
  const payload = (await response.json()) as AgentEnvelope | { error?: string };

  if (!response.ok || "error" in payload) {
    throw new Error(payload.error || "Agent request failed.");
  }

  return payload as AgentEnvelope;
}
