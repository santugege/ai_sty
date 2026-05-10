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
  currentImage: null,
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
    calls.push({ url: String(url), method: init?.method });
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
    },
    {
      url: "http://localhost:8000/api/agent/sessions/session%2Fwith%20spaces/messages",
      method: "POST",
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

test("agent route renders the workbench", () => {
  const source = readFileSync("src/app/agent/page.tsx", "utf8");

  assert.match(source, /AgentImageWorkbench/);
});

test("homepage labels the agent route as ChatGPT-style conversation", () => {
  const source = readFileSync("src/app/page.tsx", "utf8");

  assert.match(source, /ChatGPT 对话/);
  assert.doesNotMatch(source, /多轮编辑/);
});
