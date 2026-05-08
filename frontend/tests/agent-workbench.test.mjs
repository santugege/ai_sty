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
