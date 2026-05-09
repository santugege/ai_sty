import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

test("agent api client calls the single in-memory conversation routes", () => {
  const source = readFileSync("src/lib/agent-api.ts", "utf8");

  assert.match(source, /\/api\/agent\/conversation/);
  assert.match(source, /sendConversationMessage/);
  assert.match(source, /resetConversation/);
  assert.doesNotMatch(source, /createAgentSession/);
  assert.doesNotMatch(source, /restoreAgentVersion/);
  assert.doesNotMatch(source, /\/api\/agent\/sessions/);
});

test("agent workbench renders a ChatGPT-style conversation composer", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /sendConversationMessage/);
  assert.match(source, /resetConversation/);
  assert.match(source, /messages\.map/);
  assert.match(source, /selectedImages/);
  assert.match(source, /textarea/);
  assert.match(source, /ChatGPT/);
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
