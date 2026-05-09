import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const pageSource = readFileSync(new URL("../src/app/page.tsx", import.meta.url), "utf8");
const homeProductWorkbenchSource = readFileSync(
  new URL("../src/components/home-product-workbench.tsx", import.meta.url),
  "utf8",
);

test("homepage is the ecommerce product image workspace with backend-aligned fields", () => {
  assert.match(pageSource, /HomeProductWorkbench/);
  assert.match(pageSource, /getToolById\("product"\)/);
  assert.match(pageSource, /notFound/);

  assert.match(homeProductWorkbenchSource, /"use client"/);
  assert.match(homeProductWorkbenchSource, /conceptChrome/);
  assert.match(homeProductWorkbenchSource, /leftStudioRail/);
  assert.match(homeProductWorkbenchSource, /mainStudioStage/);
  assert.match(homeProductWorkbenchSource, /heroCanvas/);
  assert.match(homeProductWorkbenchSource, /emptyCanvas/);
  assert.match(homeProductWorkbenchSource, /rightInspector/);
  assert.match(homeProductWorkbenchSource, /floatingPrompt/);
  assert.match(homeProductWorkbenchSource, /purposeInspectorPanel/);
  assert.match(homeProductWorkbenchSource, /promptComposer/);
  assert.match(homeProductWorkbenchSource, /platformPresets\.map/);
  assert.match(homeProductWorkbenchSource, /productImagePurposes\.map/);
  assert.match(homeProductWorkbenchSource, /rows=\{4\}/);
  assert.match(homeProductWorkbenchSource, /min-h-\[112px\]/);
  assert.match(homeProductWorkbenchSource, /xl:right-\[423px\]/);
  assert.match(homeProductWorkbenchSource, /submitImageGenerationForm/);
  assert.match(homeProductWorkbenchSource, /new FormData\(\)/);
  assert.match(homeProductWorkbenchSource, /formData\.append\("toolId", tool\.id\)/);
  assert.match(homeProductWorkbenchSource, /formData\.append\("prompt", notes\)/);
  assert.match(homeProductWorkbenchSource, /formData\.append\("size", size\)/);
  assert.match(homeProductWorkbenchSource, /formData\.append\("platformStyle", platformStyle\)/);
  assert.match(homeProductWorkbenchSource, /formData\.append\("imagePurpose", imagePurpose\)/);
  assert.match(homeProductWorkbenchSource, /formData\.append\("image", file\)/);
  assert.match(homeProductWorkbenchSource, /type="file"/);
  assert.match(homeProductWorkbenchSource, /result\.src/);
  assert.match(homeProductWorkbenchSource, /error/);
  assert.match(homeProductWorkbenchSource, /href="\/"/);
  assert.match(homeProductWorkbenchSource, /xl:grid-cols-\[204px_minmax\(0,1fr\)_381px\]/);
  assert.match(homeProductWorkbenchSource, /rounded-\[10px\]/);
  assert.match(homeProductWorkbenchSource, /1024x1024/);
  assert.match(homeProductWorkbenchSource, /1536x1024/);
  assert.match(homeProductWorkbenchSource, /1024x1536/);

  const leftRailIndex = homeProductWorkbenchSource.indexOf("leftStudioRail");
  const mainStageIndex = homeProductWorkbenchSource.indexOf("mainStudioStage");
  const rightInspectorIndex = homeProductWorkbenchSource.indexOf("rightInspector");
  const purposeInspectorIndex = homeProductWorkbenchSource.indexOf("purposeInspectorPanel");
  assert.ok(leftRailIndex >= 0);
  assert.ok(mainStageIndex > leftRailIndex);
  assert.ok(rightInspectorIndex > mainStageIndex);
  assert.ok(purposeInspectorIndex > rightInspectorIndex);

  assert.doesNotMatch(homeProductWorkbenchSource, /styleOptions/);
  assert.doesNotMatch(homeProductWorkbenchSource, /href="\/tools\/avatar"/);
  assert.doesNotMatch(homeProductWorkbenchSource, /href="\/tools\/restore"/);
  assert.doesNotMatch(homeProductWorkbenchSource, /头像/);
  assert.doesNotMatch(homeProductWorkbenchSource, /修复/);
  assert.doesNotMatch(homeProductWorkbenchSource, /productSceneStyles/);
  assert.doesNotMatch(homeProductWorkbenchSource, /productVisualTones/);
  assert.doesNotMatch(homeProductWorkbenchSource, /productCategory/);
  assert.doesNotMatch(homeProductWorkbenchSource, /sellingPoints/);
  assert.doesNotMatch(homeProductWorkbenchSource, /promotionText/);
  assert.doesNotMatch(homeProductWorkbenchSource, /preserveRequirements/);
  assert.doesNotMatch(homeProductWorkbenchSource, /avoidElements/);
  assert.doesNotMatch(homeProductWorkbenchSource, /sceneStyle/);
  assert.doesNotMatch(homeProductWorkbenchSource, /visualTone/);
  assert.doesNotMatch(homeProductWorkbenchSource, /generate-slider/);
  assert.doesNotMatch(homeProductWorkbenchSource, /href="\/tools\/product"/);
  assert.doesNotMatch(homeProductWorkbenchSource, /purposeRailPanel/);
  assert.doesNotMatch(homeProductWorkbenchSource, /xl:right-\[112px\]/);
  assert.doesNotMatch(homeProductWorkbenchSource, /inspirationTiles/);
  assert.doesNotMatch(homeProductWorkbenchSource, /InspirationCard/);
  assert.doesNotMatch(homeProductWorkbenchSource, /previewDeck/);
  assert.doesNotMatch(homeProductWorkbenchSource, /images\.unsplash\.com/);
  assert.doesNotMatch(homeProductWorkbenchSource, /灵感库/);
  assert.doesNotMatch(homeProductWorkbenchSource, /项目/);
  assert.doesNotMatch(homeProductWorkbenchSource, /素材/);
  assert.doesNotMatch(homeProductWorkbenchSource, /text-6xl|text-7xl|text-8xl/);
  assert.doesNotMatch(homeProductWorkbenchSource, /bg-white/);
});
