import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

const globalsSource = readFileSync(new URL("../src/app/globals.css", import.meta.url), "utf8");
const toolsSource = readFileSync(new URL("../src/lib/tools.ts", import.meta.url), "utf8");
const toolPageSource = readFileSync(
  new URL("../src/app/tools/[toolId]/page.tsx", import.meta.url),
  "utf8",
);
const productWorkbenchSource = readFileSync(
  new URL("../src/components/product-workbench.tsx", import.meta.url),
  "utf8",
);
const nextConfigSource = readFileSync(new URL("../next.config.ts", import.meta.url), "utf8");
const toolCardPath = new URL("../src/components/tool-card.tsx", import.meta.url);
const toolFormPath = new URL("../src/components/tool-form.tsx", import.meta.url);

test("global theme uses a dark creative-studio color system", () => {
  assert.match(globalsSource, /--color-paper:\s*#0b0d12/);
  assert.match(globalsSource, /--color-surface:/);
  assert.match(globalsSource, /--color-cyan:/);
  assert.match(globalsSource, /--color-coral:/);
  assert.match(globalsSource, /radial-gradient/);
});

test("frontend registry exposes only the product image tool", () => {
  assert.match(toolsSource, /export type ToolId = "product"/);
  assert.match(toolsSource, /id: "product"/);
  assert.doesNotMatch(toolsSource, /id: "creator"/);
  assert.doesNotMatch(toolsSource, /id: "restore"/);
  assert.doesNotMatch(toolsSource, /id: "avatar"/);
  assert.doesNotMatch(toolsSource, /Text to image|Photo restoration|Portrait studio/);
});

test("tool detail shell is restricted to the product workbench", () => {
  assert.match(toolPageSource, /Studio Matrix/);
  assert.match(toolPageSource, /toolTopBar/);
  assert.match(toolPageSource, /bg-paper/);
  assert.match(toolPageSource, /text-ink/);
  assert.match(toolPageSource, /ProductWorkbench/);
  assert.match(toolPageSource, /notFound/);
  assert.doesNotMatch(toolPageSource, /ToolForm/);
  assert.doesNotMatch(toolPageSource, /text-6xl|text-7xl|text-8xl/);
  assert.doesNotMatch(toolPageSource, /text-paper-dim/);
});

test("generic non-product frontend components are removed", () => {
  assert.equal(existsSync(toolCardPath), false);
  assert.equal(existsSync(toolFormPath), false);
});

test("product workbench shows a non-empty canvas and persistent generation controls", () => {
  assert.match(productWorkbenchSource, /sampleShowcase/);
  assert.match(productWorkbenchSource, /conceptStudioShell/);
  assert.match(productWorkbenchSource, /leftControlPanel/);
  assert.match(productWorkbenchSource, /centerStage/);
  assert.match(productWorkbenchSource, /rightInspector/);
  assert.match(productWorkbenchSource, /生成商品图/);
  assert.match(productWorkbenchSource, /xl:grid-cols-\[/);
  assert.doesNotMatch(productWorkbenchSource, /bg-white/);
});

test("development preview hides the Next.js indicator for screenshot parity", () => {
  assert.match(nextConfigSource, /devIndicators:\s*false/);
});
