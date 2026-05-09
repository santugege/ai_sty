import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

const pageSource = readFileSync(new URL("../src/app/page.tsx", import.meta.url), "utf8");
const toolsSource = readFileSync(new URL("../src/lib/tools.ts", import.meta.url), "utf8");
const productWorkbenchSource = readFileSync(
  new URL("../src/components/product-workbench.tsx", import.meta.url),
  "utf8",
);
const homeProductWorkbenchPath = new URL(
  "../src/components/home-product-workbench.tsx",
  import.meta.url,
);

test("homepage keeps only the rail and compact product workbench", () => {
  assert.match(pageSource, /homepageShell/);
  assert.match(pageSource, /homepageRail/);
  assert.match(pageSource, /homepageWorkbenchDock/);
  assert.match(pageSource, /ProductWorkbench/);
  assert.match(pageSource, /variant="compact"/);
  assert.match(pageSource, /getToolById\("product"\)/);
  assert.match(pageSource, /notFound/);
  assert.match(pageSource, /href: "\/agent"/);
  assert.doesNotMatch(pageSource, /homepageBriefing/);
  assert.doesNotMatch(pageSource, /AI Ecommerce Command/);
  assert.doesNotMatch(pageSource, /电商商品图首页/);
  assert.doesNotMatch(pageSource, /当前工作流/);
  assert.doesNotMatch(pageSource, /打开多轮编辑工作台/);
  assert.doesNotMatch(pageSource, /HomeProductWorkbench/);
  assert.equal(existsSync(homeProductWorkbenchPath), false);

  assert.match(productWorkbenchSource, /"use client"/);
  assert.match(productWorkbenchSource, /type ProductWorkbenchVariant = "full" \| "compact"/);
  assert.match(productWorkbenchSource, /variant = "full"/);
  assert.match(productWorkbenchSource, /isCompact/);
  assert.match(productWorkbenchSource, /compactProductWorkbench/);
  assert.match(productWorkbenchSource, /xl:h-\[calc\(100vh-2\.5rem\)\]/);
  assert.match(productWorkbenchSource, /xl:h-full/);
  assert.match(productWorkbenchSource, /conceptStudioShell/);
  assert.match(productWorkbenchSource, /leftControlPanel/);
  assert.match(productWorkbenchSource, /xl:min-h-0 xl:overflow-y-auto/);
  assert.match(productWorkbenchSource, /centerStage/);
  assert.match(productWorkbenchSource, /rightInspector/);
  assert.match(productWorkbenchSource, /xl:overflow-hidden/);
  assert.match(productWorkbenchSource, /optionalSourcePanel/);
  assert.match(productWorkbenchSource, /generationSettingsPanel/);
  assert.match(productWorkbenchSource, /ParameterSelect/);
  assert.match(productWorkbenchSource, /parameterSelect/);
  assert.match(productWorkbenchSource, /descriptionById/);
  assert.match(productWorkbenchSource, /agentConversationPanel/);
  assert.match(productWorkbenchSource, /compactSummaryStrip/);
  assert.match(productWorkbenchSource, /chatInput/);
  assert.match(productWorkbenchSource, /compact=\{isCompact\}/);
  assert.match(productWorkbenchSource, /rows=\{isCompact \? 3 : 4\}/);
  assert.match(productWorkbenchSource, /productPlatformStyles/);
  assert.match(productWorkbenchSource, /productImagePurposes/);

  assert.match(productWorkbenchSource, /可选上传原图/);
  assert.match(productWorkbenchSource, /电商平台/);
  assert.match(productWorkbenchSource, /画面比例/);
  assert.match(productWorkbenchSource, /生成像素/);
  assert.match(productWorkbenchSource, /生成数量/);
  assert.match(productWorkbenchSource, /Agent 对话调整/);
  assert.match(productWorkbenchSource, /生成商品图/);

  assert.match(productWorkbenchSource, /submitImageGenerationForm/);
  assert.match(productWorkbenchSource, /new FormData\(\)/);
  assert.match(productWorkbenchSource, /formData\.append\("toolId", tool\.id\)/);
  assert.match(productWorkbenchSource, /formData\.append\("prompt", promptBrief\)/);
  assert.match(productWorkbenchSource, /formData\.append\("size", size\)/);
  assert.match(productWorkbenchSource, /formData\.append\("platformStyle", platformStyle\)/);
  assert.match(productWorkbenchSource, /formData\.append\("imagePurpose", imagePurpose\)/);
  assert.match(productWorkbenchSource, /formData\.append\("aspectRatio", aspectRatio\)/);
  assert.match(productWorkbenchSource, /formData\.append\("imageCount", imageCount\)/);
  assert.match(productWorkbenchSource, /formData\.append\("image", file\)/);
  assert.match(productWorkbenchSource, /type="file"/);
  assert.match(productWorkbenchSource, /result\.src/);
  assert.match(productWorkbenchSource, /error/);
  assert.match(productWorkbenchSource, /bg-paper/);
  assert.match(productWorkbenchSource, /imageSizes\.map/);
  assert.match(productWorkbenchSource, /imageCountOptions\.map/);
  assert.match(toolsSource, /1024x1024/);
  assert.match(toolsSource, /1536x1024/);
  assert.match(toolsSource, /1024x1536/);

  const controlsIndex = productWorkbenchSource.indexOf("leftControlPanel");
  const stageIndex = productWorkbenchSource.indexOf("centerStage");
  const inspectorIndex = productWorkbenchSource.indexOf("rightInspector");
  assert.ok(controlsIndex >= 0);
  assert.ok(stageIndex > controlsIndex);
  assert.ok(inspectorIndex > stageIndex);

  assert.doesNotMatch(productWorkbenchSource, /styleOptions/);
  assert.doesNotMatch(productWorkbenchSource, /href="\/tools\/avatar"/);
  assert.doesNotMatch(productWorkbenchSource, /href="\/tools\/restore"/);
  assert.doesNotMatch(productWorkbenchSource, /productSceneStyles/);
  assert.doesNotMatch(productWorkbenchSource, /productVisualTones/);
  assert.doesNotMatch(productWorkbenchSource, /productCategory/);
  assert.doesNotMatch(productWorkbenchSource, /sellingPoints/);
  assert.doesNotMatch(productWorkbenchSource, /promotionText/);
  assert.doesNotMatch(productWorkbenchSource, /preserveRequirements/);
  assert.doesNotMatch(productWorkbenchSource, /avoidElements/);
  assert.doesNotMatch(productWorkbenchSource, /sceneStyle/);
  assert.doesNotMatch(productWorkbenchSource, /visualTone/);
  assert.doesNotMatch(productWorkbenchSource, /promptComposer/);
  assert.doesNotMatch(productWorkbenchSource, /商品提示词/);
  assert.doesNotMatch(productWorkbenchSource, /required/);
  assert.doesNotMatch(productWorkbenchSource, /OptionGroup/);
  assert.doesNotMatch(productWorkbenchSource, /role="radiogroup"/);
  assert.doesNotMatch(productWorkbenchSource, /role="radio"/);
  assert.doesNotMatch(productWorkbenchSource, /data-option-index/);
  assert.doesNotMatch(productWorkbenchSource, /type="button"/);
  assert.doesNotMatch(productWorkbenchSource, /generate-slider/);
  assert.doesNotMatch(productWorkbenchSource, /leftStudioRail/);
  assert.doesNotMatch(productWorkbenchSource, /mainStudioStage/);
  assert.doesNotMatch(productWorkbenchSource, /floatingPrompt/);
  assert.doesNotMatch(productWorkbenchSource, /conceptChrome/);
});
