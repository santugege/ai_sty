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

test("homepage links to the readable agent workbench entry", () => {
  const source = readFileSync("src/components/home-product-workbench.tsx", "utf8");

  assert.match(source, /href: "\/agent"/);
  assert.match(source, /多轮 Agent/);
});
