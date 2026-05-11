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

test("auth api non-json errors use a stable fallback message", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async () =>
    new Response("not json", {
      status: 502,
      headers: { "content-type": "text/plain" },
    });

  const { getCurrentUser } = await importTsModule("src/lib/auth-api.ts");

  await assert.rejects(getCurrentUser(), {
    message: "Auth request failed.",
  });
});

test("auth api preserves json detail errors", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Session expired." }), {
      status: 401,
      headers: { "content-type": "application/json" },
    });

  const { getCurrentUser } = await importTsModule("src/lib/auth-api.ts");

  await assert.rejects(getCurrentUser(), {
    message: "Session expired.",
  });
});

test("auth api update user sends only allowed fields", async (t) => {
  const originalFetch = globalThis.fetch;
  let requestBody;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (_url, init) => {
    requestBody = init?.body;
    return new Response(
      JSON.stringify({
        user: {
          id: "uuid",
          userId: "U00000001",
          email: "new@example.com",
          username: "new-owner",
          isAdmin: true,
          isActive: false,
          createdAt: "2026-05-10T00:00:00Z",
          updatedAt: "2026-05-10T00:00:00Z",
        },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };

  const { updateUser } = await importTsModule("src/lib/auth-api.ts");
  await updateUser("U00000001", {
    email: "new@example.com",
    username: "new-owner",
    isActive: false,
    isAdmin: false,
  });

  assert.deepEqual(JSON.parse(requestBody), {
    email: "new@example.com",
    username: "new-owner",
    isActive: false,
  });
});

test("agent api non-json errors use a stable fallback message", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async () =>
    new Response("not json", {
      status: 502,
      headers: { "content-type": "text/plain" },
    });

  const { listAgentSessions } = await importTsModule("src/lib/agent-api.ts");

  await assert.rejects(listAgentSessions(), {
    message: "Agent request failed.",
  });
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
  assert.match(source, /finally[\s\S]*setUser\(null\)[\s\S]*router\.replace\("\/login"\)/);
});

test("login and register pages submit account forms", () => {
  const loginSource = readFileSync("src/app/login/page.tsx", "utf8");
  const registerSource = readFileSync("src/app/register/page.tsx", "utf8");

  assert.match(loginSource, /loginAccount/);
  assert.match(loginSource, /safeNextPath/);
  assert.match(loginSource, /邮箱/);
  assert.match(loginSource, /密码/);
  assert.match(loginSource, /router\.replace/);
  assert.match(loginSource, /refreshUser\(\)/);
  assert.match(registerSource, /registerAccount/);
  assert.match(registerSource, /用户名/);
  assert.match(registerSource, /邮箱/);
  assert.match(registerSource, /密码/);
  assert.match(registerSource, /refreshUser\(\)/);
});

test("login next redirect is constrained to safe local paths", async () => {
  const { safeNextPath } = await importTsModule("src/lib/safe-next-path.ts");

  assert.equal(safeNextPath("/admin/accounts"), "/admin/accounts");
  assert.equal(safeNextPath("/agent?draft=1"), "/agent?draft=1");
  assert.equal(safeNextPath(null), "/");
  assert.equal(safeNextPath("https://example.com"), "/");
  assert.equal(safeNextPath("//example.com/path"), "/");
  assert.equal(safeNextPath("javascript:alert(1)"), "/");
  assert.equal(safeNextPath("/\\evil.com/path"), "/");
  assert.equal(safeNextPath("/%5Cevil.com/path"), "/");
  assert.equal(safeNextPath("/%5C%5Cevil.com/path"), "/");
  assert.equal(safeNextPath("/%5cevil.com/path"), "/");
});

test("app navigation hides account management from regular users", () => {
  const source = readFileSync("src/components/app-nav.tsx", "utf8");

  assert.match(source, /user\?\.isAdmin/);
  assert.match(source, /\/admin\/accounts/);
  assert.match(source, /账号管理/);
  assert.match(source, /logout/);
  assert.match(source, /mobileNav/);
  assert.match(source, /xl:hidden/);
  assert.match(source, /user\?\.email/);
});

test("admin accounts page does not provide admin promotion", () => {
  const source = readFileSync("src/app/admin/accounts/page.tsx", "utf8");

  assert.match(source, /AppShell/);
  assert.match(source, /listUsers/);
  assert.match(source, /updateUser/);
  assert.match(source, /resetUserPassword/);
  assert.match(source, /isActive/);
  assert.match(source, /caption/);
  assert.doesNotMatch(source, /isAdmin: true/);
  assert.doesNotMatch(source, /设置为管理员/);
});
