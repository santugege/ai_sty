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

test("global theme uses the light ecommerce command-center color system", () => {
  assert.match(globalsSource, /--color-paper:\s*#f4f5f0/i);
  assert.match(globalsSource, /--color-surface:\s*#ffffff/i);
  assert.match(globalsSource, /--color-cyan:\s*#0f8d7b/i);
  assert.match(globalsSource, /--color-coral:\s*#e9563e/i);
  assert.match(globalsSource, /--color-border:\s*#d8ddd2/i);
  assert.match(globalsSource, /color-scheme:\s*light/);
  assert.match(globalsSource, /command-card/);
  assert.match(globalsSource, /command-grid/);
  assert.doesNotMatch(globalsSource, /color-scheme:\s*dark/);
});

test("frontend registry exposes only the product image tool with readable labels", () => {
  assert.match(toolsSource, /export type ToolId = "product"/);
  assert.match(toolsSource, /id: "product"/);
  assert.match(toolsSource, /电商商品图工作台/);
  assert.match(toolsSource, /淘宝\/天猫/);
  assert.match(toolsSource, /主图/);
  assert.doesNotMatch(toolsSource, /id: "creator"/);
  assert.doesNotMatch(toolsSource, /id: "restore"/);
  assert.doesNotMatch(toolsSource, /id: "avatar"/);
  assert.doesNotMatch(toolsSource, /Text to image|Photo restoration|Portrait studio/);
  assert.doesNotMatch(toolsSource, /export type ImageTool = \{[^}]*description/s);
  assert.doesNotMatch(toolsSource, /sizeOptions/);
});

test("tool detail shell is restricted to the product workbench", () => {
  assert.match(toolPageSource, /AppShell/);
  assert.match(toolPageSource, /bg-paper/);
  assert.match(toolPageSource, /text-ink/);
  assert.match(toolPageSource, /ProductWorkbench/);
  assert.match(toolPageSource, /notFound/);
  assert.doesNotMatch(toolPageSource, /Studio Matrix/);
  assert.doesNotMatch(toolPageSource, /toolTopBar/);
  assert.doesNotMatch(toolPageSource, /ToolForm/);
  assert.doesNotMatch(toolPageSource, /text-6xl|text-7xl|text-8xl/);
  assert.doesNotMatch(toolPageSource, /text-paper-dim/);
});

test("generic non-product frontend components are removed", () => {
  assert.equal(existsSync(toolCardPath), false);
  assert.equal(existsSync(toolFormPath), false);
});

test("product detail workbench still shows a non-empty canvas and persistent generation controls", () => {
  assert.match(productWorkbenchSource, /sampleShowcase/);
  assert.match(productWorkbenchSource, /conceptStudioShell/);
  assert.match(productWorkbenchSource, /leftControlPanel/);
  assert.match(productWorkbenchSource, /centerStage/);
  assert.match(productWorkbenchSource, /rightInspector/);
  assert.match(productWorkbenchSource, /生成商品图|鐢熸垚鍟嗗搧鍥?/);
  assert.match(productWorkbenchSource, /xl:grid-cols-\[/);
});

test("product detail workbench supports required upload and prompt preview workflow", () => {
  assert.match(toolsSource, /2048x2048/);
  assert.match(toolsSource, /2048x1152/);
  assert.match(toolsSource, /3840x2160/);
  assert.match(toolsSource, /2160x3840/);

  assert.match(productWorkbenchSource, /requiredSourcePanel/);
  assert.match(productWorkbenchSource, /generationSettingsPanel/);
  assert.match(productWorkbenchSource, /promptPreviewPanel/);
  assert.match(productWorkbenchSource, /必须上传原图/);
  assert.match(productWorkbenchSource, /电商平台/);
  assert.match(productWorkbenchSource, /画面比例/);
  assert.match(productWorkbenchSource, /生成像素/);
  assert.match(productWorkbenchSource, /生成数量/);
  assert.match(productWorkbenchSource, /最终提示词预览/);
  assert.match(productWorkbenchSource, /用户需求/);
  assert.match(productWorkbenchSource, /只读预览/);
  assert.match(productWorkbenchSource, /finalPromptPreview/);
  assert.match(productWorkbenchSource, /userRequirement/);
  assert.match(productWorkbenchSource, /if \(!file\)/);
  assert.match(productWorkbenchSource, /formData\.append\("aspectRatio", aspectRatio\)/);
  assert.match(productWorkbenchSource, /formData\.append\("imageCount", imageCount\)/);
  assert.match(productWorkbenchSource, /formData\.append\("prompt", finalPromptPreview\)/);
  assert.doesNotMatch(productWorkbenchSource, /chatMessages/);
  assert.doesNotMatch(productWorkbenchSource, /chatInput/);
  assert.doesNotMatch(productWorkbenchSource, /Agent Conversation/);
  assert.doesNotMatch(productWorkbenchSource, /productSceneStyles/);
  assert.doesNotMatch(productWorkbenchSource, /productVisualTones/);
  assert.doesNotMatch(productWorkbenchSource, /productCategory/);
  assert.doesNotMatch(productWorkbenchSource, /sellingPoints/);
  assert.doesNotMatch(productWorkbenchSource, /promotionText/);
  assert.doesNotMatch(productWorkbenchSource, /preserveRequirements/);
  assert.doesNotMatch(productWorkbenchSource, /avoidElements/);
  assert.doesNotMatch(productWorkbenchSource, /Additional Directives/);
  assert.doesNotMatch(productWorkbenchSource, /Key Selling Points/);
  assert.doesNotMatch(productWorkbenchSource, /Product Category/);
});

test("development preview hides the Next.js indicator for screenshot parity", () => {
  assert.match(nextConfigSource, /devIndicators:\s*false/);
});
