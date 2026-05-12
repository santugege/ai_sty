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
  assert.match(source, /streamAgentSession/);
  assert.match(source, /streamAgentSessionMessage/);
  assert.match(source, /\/api\/agent\/sessions/);
  assert.match(source, /\/api\/agent\/sessions\/stream/);
  assert.match(source, /\/messages\/stream/);
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

test("agent api client parses server-sent stream events", async (t) => {
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
    return new Response(
      [
        "event: assistant_delta",
        'data: {"delta":"Hel"}',
        "",
        "event: assistant_delta",
        'data: {"delta":"lo"}',
        "",
        "event: final",
        `data: ${JSON.stringify(successEnvelope)}`,
        "",
      ].join("\n"),
      {
        headers: { "content-type": "text/event-stream" },
        status: 200,
      },
    );
  };

  const { streamAgentSession } = await importAgentApiClient();
  const events = [];
  await streamAgentSession(new FormData(), (event) => events.push(event));

  assert.deepEqual(calls, [
    {
      url: "http://localhost:8000/api/agent/sessions/stream",
      method: "POST",
      credentials: "include",
    },
  ]);
  assert.deepEqual(events.map((event) => event.event), [
    "assistant_delta",
    "assistant_delta",
    "final",
  ]);
  assert.equal(events[0].data.delta, "Hel");
  assert.equal(events[1].data.delta, "lo");
  assert.equal(events[2].data.conversation.id, "session-1");
});

test("agent api client can abort streamed session requests", async (t) => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (url, init) => {
    calls.push({
      url: String(url),
      method: init?.method,
      signal: init?.signal,
    });
    return new Response("", {
      headers: { "content-type": "text/event-stream" },
      status: 200,
    });
  };

  const { streamAgentSession, streamAgentSessionMessage } =
    await importAgentApiClient();
  const controller = new AbortController();
  await streamAgentSession(new FormData(), () => undefined, controller.signal);
  await streamAgentSessionMessage(
    "session-1",
    new FormData(),
    () => undefined,
    controller.signal,
  );

  assert.equal(calls.length, 2);
  assert.equal(calls[0].signal, controller.signal);
  assert.equal(calls[1].signal, controller.signal);
});

test("agent workbench renders session list and sends to active session", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /listAgentSessions/);
  assert.match(source, /getAgentSession/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /sendAgentSessionMessage/);
  assert.match(source, /streamAgentSession/);
  assert.match(source, /streamAgentSessionMessage/);
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

test("agent workbench sends configurable image quality and shared product sizes", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");
  const toolsSource = readFileSync("src/lib/tools.ts", "utf8");

  assert.match(source, /imageSizes/);
  assert.match(source, /imageQualities/);
  assert.match(source, /useState<ImageSize>\("1536x1024"\)/);
  assert.match(source, /useState<ImageQuality>\("auto"\)/);
  assert.match(source, /formData\.append\("quality", quality\)/);
  assert.match(source, /setQuality\(event\.target\.value as ImageQuality\)/);
  assert.match(toolsSource, /export const imageQualities = \[/);
  assert.match(toolsSource, /"2048x2048"/);
  assert.match(toolsSource, /"3840x2160"/);
  assert.doesNotMatch(
    source,
    /const imageSizes = \["1024x1024", "1536x1024", "1024x1536"\] as const/,
  );
});

test("agent workbench shows receiving state in the message stream after submit", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /const draftMessage = messageOverride \?\? message/);
  assert.match(source, /const draftImages = imagesOverride \?\? selectedImages/);
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
  assert.match(source, /生成图片/);
  assert.doesNotMatch(source, /Loader2/);
});

test("agent workbench rotates frontend-only generation status copy", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /agentLoadingPhrases/);
  assert.match(source, /生成图片/);
  assert.match(source, /添加细节/);
  assert.match(source, /润色画面/);
  assert.match(source, /保存图片/);
  assert.match(source, /setLoadingPhraseIndex/);
  assert.match(source, /window\.setInterval/);
  assert.match(source, /ReceivingBubble phrase=\{agentLoadingPhrases\[loadingPhraseIndex\]\}/);
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

test("agent workbench appends streamed assistant deltas before final envelope", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /streamingAssistantMessage/);
  assert.match(source, /createStreamingAssistantMessage/);
  assert.match(source, /appendAssistantDelta/);
  assert.match(source, /assistant_delta/);
  assert.match(source, /setStreamingAssistantMessage/);
  assert.match(source, /streamingAssistantMessage && \([\s\S]*<MessageBubble/);
});

test("agent workbench exposes ChatGPT-style message actions", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /handleCopyMessage/);
  assert.match(source, /handleEditMessage/);
  assert.match(source, /handleRegenerateMessage/);
  assert.match(source, /MessageActionBar/);
  assert.match(source, /复制/);
  assert.match(source, /编辑再发/);
  assert.match(source, /重新生成/);
});

test("agent workbench regenerate immediately resubmits the previous user message", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");
  const regenerateBlock = source.slice(
    source.indexOf("function handleRegenerateMessage"),
    source.indexOf("function handleContinueEditingImage"),
  );

  assert.match(source, /submitAgentMessage/);
  assert.match(regenerateBlock, /void submitAgentMessage\(\{ messageOverride: previousUserMessage\.content \}\)/);
  assert.doesNotMatch(regenerateBlock, /setMessage\(previousUserMessage\.content\)/);
});

test("agent workbench can stop a streaming generation request", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /AbortController/);
  assert.match(source, /activeStreamControllerRef/);
  assert.match(source, /handleStopGeneration/);
  assert.match(source, /streamAgentSessionMessage\(activeSessionId, formData, handleStreamEvent, signal\)/);
  assert.match(source, /streamAgentSession\(formData, handleStreamEvent, signal\)/);
  assert.match(source, /停止生成/);
});

test("agent generated images expose a continue editing entry", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /handleContinueEditingImage/);
  assert.match(source, /onContinueEditingImage/);
  assert.match(source, /继续编辑/);
  assert.match(source, /基于这张图继续编辑/);
});

test("agent workbench does not render a dedicated current image context panel", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.doesNotMatch(source, /currentImage/);
  assert.doesNotMatch(source, /max-h-56/);
});

test("agent generated images can be previewed and downloaded", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");
  const actionsSource = readFileSync(
    "src/components/generated-image-actions.tsx",
    "utf8",
  );

  assert.match(source, /ImagePreviewDialog/);
  assert.match(source, /GeneratedImageActions/);
  assert.match(source, /setPreviewImage/);
  assert.match(source, /onPreviewImage/);
  assert.match(actionsSource, /Download/);
  assert.match(actionsSource, /ExternalLink/);
  assert.match(actionsSource, /download=/);
  assert.match(actionsSource, /href=\{image\.src\}/);
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

test("agent workbench keeps the chat pane flush with the session list", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");
  const chatPaneMarkup = source.slice(
    source.indexOf("flex w-full flex-col"),
    source.indexOf("<header className"),
  );

  assert.match(chatPaneMarkup, /flex w-full flex-col/);
  assert.equal(chatPaneMarkup.includes("max-w-5xl"), false);
  assert.equal(chatPaneMarkup.includes("mx-auto"), false);
});

test("homepage labels the agent route as ChatGPT-style conversation", () => {
  const source = readFileSync("src/components/app-nav.tsx", "utf8");

  assert.match(source, /ChatGPT 对话/);
  assert.doesNotMatch(source, /多轮编辑/);
});

