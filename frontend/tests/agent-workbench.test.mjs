import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

test("agent api client calls the agent routes", () => {
  const source = readFileSync("src/lib/agent-api.ts", "utf8");

  assert.match(source, /\/api\/agent\/sessions/);
  assert.match(source, /createAgentSession/);
  assert.match(source, /sendAgentMessage/);
  assert.match(source, /restoreAgentVersion/);
});

test("agent workbench renders chat, current image, and version restore controls", () => {
  const source = readFileSync("src/components/agent-image-workbench.tsx", "utf8");

  assert.match(source, /createAgentSession/);
  assert.match(source, /sendAgentMessage/);
  assert.match(source, /restoreAgentVersion/);
  assert.match(source, /versions\.map/);
  assert.match(source, /textarea/);
});

test("agent route renders the workbench", () => {
  const source = readFileSync("src/app/agent/page.tsx", "utf8");

  assert.match(source, /AgentImageWorkbench/);
});

test("product workbench uses prompt preview instead of embedded agent chat", () => {
  const source = readFileSync("src/components/product-workbench.tsx", "utf8");

  assert.match(source, /promptPreviewPanel/);
  assert.match(source, /finalPromptPreview/);
  assert.match(source, /userRequirement/);
  assert.doesNotMatch(source, /agentConversationPanel/);
  assert.doesNotMatch(source, /Agent Conversation/);
  assert.doesNotMatch(source, /chatMessages\.map/);
});
