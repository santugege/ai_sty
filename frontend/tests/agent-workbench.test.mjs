import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";
import ts from "typescript";

async function importAgentApiClient() {
  const source = readFileSync("src/lib/agent-api.ts", "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  });
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}#${Date.now()}-${Math.random()}`;

  return import(moduleUrl);
}

const successEnvelope = {
  conversation: {
    id: "session-1",
    title: "Session one",
    summary: null,
    previousResponseId: null,
    status: "ready",
    createdAt: "2026-05-10T00:00:00Z",
    updatedAt: "2026-05-10T00:00:00Z",
  },
  messages: [
    {
      id: "message-1",
      role: "assistant",
      content: "Ready",
      attachments: [],
      responseId: null,
      imageVersionId: "version-1",
      image: null,
      createdAt: "2026-05-10T00:00:00Z",
    },
  ],
  error: null,
};

test("agent api client uses persisted session routes", () => {
  const source = readFileSync("src/lib/agent-api.ts", "utf8");

  assert.match(source, /listAgentSessions/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /getAgentSession/);
  assert.match(source, /sendAgentSessionMessage/);
  assert.match(source, /\/api\/agent\/sessions/);
  assert.match(source, /imageVersionId\?: string \| null/);
  assert.match(source, /image\?: ConversationImage \| null/);
  assert.doesNotMatch(source, /currentImage\?:/);
  assert.doesNotMatch(source, /sendConversationMessage/);
  assert.doesNotMatch(source, /resetConversation/);
  assert.doesNotMatch(source, /\/api\/agent\/conversation/);
});

test("agent api client accepts successful envelopes with null errors", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async () =>
    new Response(JSON.stringify(successEnvelope), {
      headers: { "content-type": "application/json" },
      status: 200,
    });

  const { createAgentSession } = await importAgentApiClient();
  const envelope = await createAgentSession(new FormData());

  assert.equal(envelope.error, null);
  assert.equal(envelope.messages[0].imageVersionId, "version-1");
});

test("agent api client encodes session ids in persisted routes", async (t) => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (url, init) => {
    calls.push({
      url: String(url),
      method: init?.method,
      credentials: init?.credentials,
    });
    return new Response(JSON.stringify(successEnvelope), {
      headers: { "content-type": "application/json" },
      status: 200,
    });
  };

  const { getAgentSession, sendAgentSessionMessage } = await importAgentApiClient();
  await getAgentSession("session/with spaces");
  await sendAgentSessionMessage("session/with spaces", new FormData());

  assert.deepEqual(calls, [
    {
      url: "http://localhost:8000/api/agent/sessions/session%2Fwith%20spaces",
      method: "GET",
      credentials: "include",
    },
    {
      url: "http://localhost:8000/api/agent/sessions/session%2Fwith%20spaces/messages",
      method: "POST",
      credentials: "include",
    },
  ]);
});

test("agent workbench renders session list and sends to active session", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /listAgentSessions/);
  assert.match(source, /getAgentSession/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /sendAgentSessionMessage/);
  assert.match(source, /sessions\.map/);
  assert.match(source, /activeSessionId/);
  assert.match(source, /New conversation|新会话/);
});

test("agent workbench guards async session loads and clears drafts on session changes", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /requestSequenceRef/);
  assert.match(source, /beginRequest/);
  assert.match(source, /isCurrentRequest/);
  assert.match(source, /isMountedRef/);
  assert.match(source, /clearDraft/);
  assert.match(source, /handleSelectSession[\s\S]*clearDraft/);
  assert.match(source, /handleNewSession[\s\S]*beginRequest/);
  assert.match(source, /disabled=\{isSubmitting\}[\s\S]*handleSelectSession/);
  assert.match(source, /refreshSessions[\s\S]*setIsLoadingSessions\(false\)/);
  assert.match(source, /catch \(refreshError\)[\s\S]*setIsLoadingSessions\(false\)/);
});

test("agent workbench revokes discarded previews and keeps composer controls responsive", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /droppedImages/);
  assert.match(source, /revokeSelectedImages\(droppedImages\)/);
  assert.match(source, /selectedImagesRef/);
  assert.match(source, /return \(\) => revokeSelectedImages\(selectedImagesRef\.current\)/);
  assert.match(source, /flex-wrap/);
  assert.match(source, /min-w-0/);
});

test("agent workbench renders a ChatGPT-style conversation composer", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /sendAgentSessionMessage/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /messages\.map/);
  assert.match(source, /selectedImages/);
  assert.match(source, /textarea/);
  assert.match(source, /ChatGPT/);
  assert.doesNotMatch(source, /sendConversationMessage/);
  assert.doesNotMatch(source, /resetConversation/);
  assert.doesNotMatch(source, /versions\.map/);
  assert.doesNotMatch(source, /restoreAgentVersion/);
  assert.doesNotMatch(source, /handleRestore/);
});

test("agent workbench shows receiving state in the message stream after submit", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /const draftMessage = message/);
  assert.match(source, /const draftImages = selectedImages/);
  assert.match(source, /pendingUserMessage/);
  assert.match(source, /createPendingUserMessage/);
  assert.match(source, /setPendingUserMessage\(createPendingUserMessage\(draftMessage, draftImages\)\)/);
  assert.match(source, /pendingUserMessage && \([\s\S]*<MessageBubble/);
  assert.match(source, /clearDraft\(draftImages, false\)/);
  assert.match(source, /revokeSelectedImages\(draftImages\)/);
  assert.match(source, /isAwaitingAgentResponse/);
  assert.match(source, /setIsAwaitingAgentResponse\(true\)/);
  assert.match(source, /setIsAwaitingAgentResponse\(false\)/);
  assert.match(source, /ReceivingBubble/);
  assert.match(source, /正在接收回复/);
  assert.doesNotMatch(source, /Loader2/);
});

test("agent workbench keeps internal summaries out of the session list", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");
  const sessionListMarkup = source.slice(
    source.indexOf("{sessions.map"),
    source.indexOf("{isLoadingSessions"),
  );

  assert.match(sessionListMarkup, /session\.title/);
  assert.doesNotMatch(sessionListMarkup, /session\.summary/);
});

test("agent workbench does not render a dedicated current image context panel", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.doesNotMatch(source, /currentImage/);
  assert.doesNotMatch(source, /ConversationImage/);
  assert.doesNotMatch(source, /max-h-56/);
});

test("agent route renders the workbench", () => {
  const source = readFileSync("src/app/agent/page.tsx", "utf8");

  assert.match(source, /AppShell/);
  assert.match(source, /AgentImageWorkbench/);
  assert.match(source, /variant="compact"/);
  assert.doesNotMatch(source, /return <AgentImageWorkbench \/>/);
});

test("agent workbench supports embedded compact shell styling", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /type AgentImageWorkbenchVariant = "full" \| "compact"/);
  assert.match(source, /variant = "full"/);
  assert.match(source, /isCompact/);
  assert.match(source, /agentWorkbenchShell/);
  assert.match(source, /compactAgentWorkbench/);
  assert.match(source, /bg-paper/);
  assert.match(source, /bg-surface/);
  assert.doesNotMatch(source, /bg-\[#f7f7f4\]/);
  assert.doesNotMatch(source, /border-\[#deded8\]/);
});

test("homepage labels the agent route as ChatGPT-style conversation", () => {
  const source = readFileSync("src/components/app-nav.tsx", "utf8");

  assert.match(source, /ChatGPT 对话/);
  assert.doesNotMatch(source, /多轮编辑/);
});

