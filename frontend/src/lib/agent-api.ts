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
  image?: ConversationImage | null;
  createdAt: string;
};

export type AgentEnvelope = {
  conversation: {
    id: string;
    title: string;
    previousResponseId?: string | null;
    status: string;
    createdAt: string;
    updatedAt: string;
  };
  messages: ConversationMessage[];
  currentImage?: ConversationImage | null;
  error?: string | null;
};

export async function sendConversationMessage(formData: FormData) {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/conversation`, {
      method: "POST",
      body: formData,
    }),
  );
}

export async function resetConversation() {
  return readAgentResponse(
    await fetch(`${apiBaseUrl}/api/agent/conversation/reset`, {
      method: "POST",
    }),
  );
}

async function readAgentResponse(response: Response): Promise<AgentEnvelope> {
  const payload = (await response.json()) as AgentEnvelope | { error?: string };

  if (!response.ok || "error" in payload) {
    throw new Error(payload.error || "Agent request failed.");
  }

  return payload as AgentEnvelope;
}
