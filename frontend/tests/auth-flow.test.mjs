import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";
import ts from "typescript";

async function importTsModule(path) {
  const source = readFileSync(path, "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2022,
    },
  });
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}#${Date.now()}-${Math.random()}`;
  return import(moduleUrl);
}

test("auth api client exposes account flow and uses cookie credentials", () => {
  const source = readFileSync("src/lib/auth-api.ts", "utf8");

  assert.match(source, /loginAccount/);
  assert.match(source, /registerAccount/);
  assert.match(source, /logoutAccount/);
  assert.match(source, /getCurrentUser/);
  assert.match(source, /listUsers/);
  assert.match(source, /updateUser/);
  assert.match(source, /resetUserPassword/);
  assert.match(source, /credentials: "include"/);
  assert.doesNotMatch(source, /isAdmin.*payload/);
});

test("auth api returns current user envelopes", async (t) => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), method: init?.method, credentials: init?.credentials });
    return new Response(
      JSON.stringify({
        user: {
          id: "uuid",
          userId: "U00000001",
          email: "owner@example.com",
          username: "owner",
          isAdmin: true,
          isActive: true,
          createdAt: "2026-05-10T00:00:00Z",
          updatedAt: "2026-05-10T00:00:00Z",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };

  const { getCurrentUser } = await importTsModule("src/lib/auth-api.ts");
  const envelope = await getCurrentUser();

  assert.equal(envelope.user.userId, "U00000001");
  assert.deepEqual(calls, [
    {
      url: "http://localhost:8000/api/auth/me",
      method: "GET",
      credentials: "include",
    },
  ]);
});

test("existing api clients send cookies and read detail errors", () => {
  const agentSource = readFileSync("src/lib/agent-api.ts", "utf8");
  const imageSource = readFileSync("src/lib/image-api.ts", "utf8");

  assert.match(agentSource, /credentials: "include"/);
  assert.match(agentSource, /payload\.detail/);
  assert.match(imageSource, /credentials: "include"/);
  assert.match(imageSource, /payload\.detail/);
});

test("auth provider protects private routes and leaves login register public", () => {
  const source = readFileSync("src/components/auth-provider.tsx", "utf8");

  assert.match(source, /publicPaths/);
  assert.match(source, /\/login/);
  assert.match(source, /\/register/);
  assert.match(source, /router\.replace/);
  assert.match(source, /AuthContext/);
});
