# Product Image Experience Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the current product image generator into a unified ecommerce image production workflow with product brief fields, multi-candidate results, generation status, and edit handoff.

**Architecture:** Keep FastAPI's existing `/api/images/generate` route for first-pass candidates and reuse the existing `/api/agent` namespace for selected-image editing. Most changes happen in the Next.js frontend: API helper types, `ProductWorkbench` state and layout, source-level tests, and browser verification. Backend changes are limited to fixing user-facing Chinese text if mojibake is confirmed in touched files.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind CSS v4, lucide-react, FastAPI, pytest, Node test runner.

---

## File Structure

- Modify `frontend/src/lib/image-api.ts`: return the full image generation envelope so the product workbench can render all candidates.
- Modify `frontend/src/components/product-workbench.tsx`: add product brief fields, staged generation status, candidate selection, result thumbnails, download action, and selected-candidate edit handoff affordance.
- Modify `frontend/src/components/agent-image-workbench.tsx`: keep the standalone agent editor intact unless shared copy or helper changes are needed.
- Modify `frontend/src/lib/agent-api.ts`: keep existing agent calls; only add a helper if the selected-candidate handoff needs a data URL to `File` conversion outside the component.
- Modify `frontend/tests/homepage-layout.test.mjs`: update source-level expectations for product brief fields, candidate rendering, staged status, and removal of mojibake expectations.
- Modify `frontend/tests/visual-refinement.test.mjs`: update visual source expectations to match the optimized workbench.
- Add `frontend/tests/product-workbench-flow.test.mjs`: source-level regression coverage for multi-image payload handling, selected candidate state, and agent handoff markers.
- Optionally modify `backend/app/main.py`, `backend/app/image_request.py`, `backend/app/tools.py`, and backend tests only if their user-facing Chinese strings are confirmed to be mojibake in the running UI or API responses.

## Task 1: Image API Envelope

**Files:**
- Modify: `frontend/src/lib/image-api.ts`
- Test: `frontend/tests/product-workbench-flow.test.mjs`

- [ ] **Step 1: Write the failing source test**

Create `frontend/tests/product-workbench-flow.test.mjs`:

```js
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const imageApiSource = readFileSync("src/lib/image-api.ts", "utf8");
const productWorkbenchSource = readFileSync(
  "src/components/product-workbench.tsx",
  "utf8",
);

test("image api exposes all generated candidates", () => {
  assert.match(imageApiSource, /export type ImageGenerationResult/);
  assert.match(imageApiSource, /images: GeneratedImage\[\]/);
  assert.match(imageApiSource, /submitImageGenerationForm\([\s\S]*Promise<ImageGenerationResult>/);
  assert.match(imageApiSource, /payload\.images \?\? \(payload\.image \? \[payload\.image\] : \[\]\)/);
});

test("product workbench tracks candidates and selected candidate", () => {
  assert.match(productWorkbenchSource, /const \[candidates, setCandidates\]/);
  assert.match(productWorkbenchSource, /const \[selectedCandidateIndex, setSelectedCandidateIndex\]/);
  assert.match(productWorkbenchSource, /selectedCandidate/);
  assert.match(productWorkbenchSource, /candidates\.map/);
  assert.match(productWorkbenchSource, /方案/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: FAIL because `ImageGenerationResult`, `candidates`, and `selectedCandidateIndex` do not exist yet.

- [ ] **Step 3: Update API helper types and return value**

In `frontend/src/lib/image-api.ts`, replace the current payload and helper implementation with this shape:

```ts
import type { ImageSize } from "@/lib/tools";

export type GeneratedImage = {
  src: string;
  mimeType: string;
  revisedPrompt?: string | null;
};

export type ImageGenerationResult = {
  image: GeneratedImage;
  images: GeneratedImage[];
};

type ImageGenerationPayload = {
  image?: GeneratedImage;
  images?: GeneratedImage[];
  error?: string;
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export const genericErrorMessage = "图片生成失败，请稍后重试。";

export function getImageDimensions(size: ImageSize) {
  const [width, height] = size.split("x").map(Number) as [number, number];

  return { width, height };
}

export async function submitImageGenerationForm(
  formData: FormData,
): Promise<ImageGenerationResult> {
  const response = await fetch(`${apiBaseUrl}/api/images/generate`, {
    method: "POST",
    body: formData,
  });
  const payload = await readImageGenerationPayload(response);
  const images = payload.images ?? (payload.image ? [payload.image] : []);
  const image = payload.image ?? images[0];

  if (!response.ok || !image || images.length === 0) {
    throw new Error(payload.error || genericErrorMessage);
  }

  return { image, images };
}

async function readImageGenerationPayload(
  response: Response,
): Promise<ImageGenerationPayload> {
  const contentType = response.headers.get("content-type")?.toLowerCase();

  if (!contentType?.includes("json")) {
    return {};
  }

  try {
    return (await response.json()) as ImageGenerationPayload;
  } catch {
    return {};
  }
}
```

- [ ] **Step 4: Run test to verify API helper passes and component expectations still fail**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: FAIL only on product workbench expectations for candidate state.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/image-api.ts frontend/tests/product-workbench-flow.test.mjs
git commit -m "feat: expose product image candidates"
```

## Task 2: Product Brief Fields

**Files:**
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/tests/homepage-layout.test.mjs`
- Modify: `frontend/tests/visual-refinement.test.mjs`

- [ ] **Step 1: Write failing source expectations**

In `frontend/tests/homepage-layout.test.mjs`, replace the assertions that product-specific fields do not exist:

```js
assert.doesNotMatch(productWorkbenchSource, /productCategory/);
assert.doesNotMatch(productWorkbenchSource, /sellingPoints/);
assert.doesNotMatch(productWorkbenchSource, /preserveRequirements/);
assert.doesNotMatch(productWorkbenchSource, /avoidElements/);
```

with:

```js
assert.match(productWorkbenchSource, /productCategory/);
assert.match(productWorkbenchSource, /sellingPoints/);
assert.match(productWorkbenchSource, /preserveRequirements/);
assert.match(productWorkbenchSource, /avoidElements/);
assert.match(productWorkbenchSource, /商品提示词/);
assert.match(productWorkbenchSource, /核心卖点/);
assert.match(productWorkbenchSource, /严格保留/);
assert.match(productWorkbenchSource, /负面限制/);
assert.match(productWorkbenchSource, /formData\.append\("productCategory", productCategory\)/);
assert.match(productWorkbenchSource, /formData\.append\("sellingPoints", sellingPoints\)/);
assert.match(productWorkbenchSource, /formData\.append\("preserveRequirements", preserveRequirements\)/);
assert.match(productWorkbenchSource, /formData\.append\("avoidElements", avoidElements\)/);
```

In `frontend/tests/visual-refinement.test.mjs`, add:

```js
assert.match(productWorkbenchSource, /Product brief/);
assert.match(productWorkbenchSource, /商品提示词/);
assert.match(productWorkbenchSource, /核心卖点/);
assert.match(productWorkbenchSource, /严格保留/);
assert.match(productWorkbenchSource, /负面限制/);
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend
npm test -- homepage-layout.test.mjs visual-refinement.test.mjs
```

Expected: FAIL because the product brief fields are not present.

- [ ] **Step 3: Add brief state and prompt composition**

In `ProductWorkbench`, add state near the existing `chatInput` state:

```ts
const [productCategory, setProductCategory] = useState("");
const [sellingPoints, setSellingPoints] = useState("");
const [preserveRequirements, setPreserveRequirements] = useState("");
const [avoidElements, setAvoidElements] = useState("");
```

Replace `promptBrief` with:

```ts
const promptBrief = [
  `平台：${selectedPlatform?.label || platformStyle}`,
  `图片类型：${selectedPurpose?.label || imagePurpose}`,
  `画面比例：${selectedAspectRatio?.label || aspectRatio}`,
  `生成像素：${size}`,
  `生成数量：${imageCount}`,
  productCategory.trim() ? `商品类目：${productCategory.trim()}` : "",
  sellingPoints.trim() ? `核心卖点：${sellingPoints.trim()}` : "",
  preserveRequirements.trim()
    ? `严格保留：${preserveRequirements.trim()}`
    : "",
  avoidElements.trim() ? `负面限制：${avoidElements.trim()}` : "",
  chatInput.trim() ? `调整要求：${chatInput.trim()}` : "",
]
  .filter(Boolean)
  .join("\n");
```

In `handleSubmit`, after `imageCount`, append:

```ts
formData.append("productCategory", productCategory);
formData.append("sellingPoints", sellingPoints);
formData.append("preserveRequirements", preserveRequirements);
formData.append("avoidElements", avoidElements);
```

- [ ] **Step 4: Add text fields to the input panel**

Create a reusable text area helper below `ParameterSelect`:

```tsx
function BriefTextarea({
  title,
  value,
  onChange,
  placeholder,
  disabled,
  rows = 3,
}: {
  title: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  disabled: boolean;
  rows?: number;
}) {
  return (
    <label className="block text-xs font-bold uppercase tracking-[0.18em] text-ink-lighter focus-within:text-cyan">
      {title}
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
        className="mt-2 w-full resize-none rounded-lg border border-border bg-paper-subtle px-3 py-2 text-sm leading-6 text-ink outline-none transition-refined placeholder:text-ink-lighter focus:border-cyan disabled:opacity-50"
      />
    </label>
  );
}
```

Add this block after the upload control and before strategy selects:

```tsx
<div className={classNames("productBriefPanel grid", isCompact ? "mt-4 gap-3" : "mt-6 gap-4")}>
  <PanelHeader
    icon={<Sparkles aria-hidden="true" className="h-5 w-5" />}
    eyebrow="Product brief"
    title="商品 Brief"
    compact={isCompact}
  />
  <BriefTextarea
    title="商品提示词"
    value={productCategory}
    onChange={setProductCategory}
    placeholder="例如：夏季桌面小风扇、护肤精华、运动鞋"
    disabled={isSubmitting}
    rows={2}
  />
  <BriefTextarea
    title="核心卖点"
    value={sellingPoints}
    onChange={setSellingPoints}
    placeholder="例如：三档风力、USB 充电、桌面与手持两用"
    disabled={isSubmitting}
  />
  <BriefTextarea
    title="严格保留"
    value={preserveRequirements}
    onChange={setPreserveRequirements}
    placeholder="例如：品牌 logo、包装文字、商品颜色、外观比例"
    disabled={isSubmitting}
  />
  <BriefTextarea
    title="负面限制"
    value={avoidElements}
    onChange={setAvoidElements}
    placeholder="例如：不要虚构配件，不要改变包装颜色，不要夸大功效"
    disabled={isSubmitting}
  />
</div>
```

- [ ] **Step 5: Run frontend source tests**

Run:

```bash
cd frontend
npm test -- homepage-layout.test.mjs visual-refinement.test.mjs
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/product-workbench.tsx frontend/tests/homepage-layout.test.mjs frontend/tests/visual-refinement.test.mjs
git commit -m "feat: add product brief fields"
```

## Task 3: Candidate Rendering

**Files:**
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/tests/product-workbench-flow.test.mjs`

- [ ] **Step 1: Add failing candidate UI expectations**

Append to `frontend/tests/product-workbench-flow.test.mjs`:

```js
test("product workbench renders candidate actions", () => {
  assert.match(productWorkbenchSource, /candidateStrip/);
  assert.match(productWorkbenchSource, /selectedCandidateIndex === index/);
  assert.match(productWorkbenchSource, /setSelectedCandidateIndex\(index\)/);
  assert.match(productWorkbenchSource, /下载图片/);
  assert.match(productWorkbenchSource, /继续编辑/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: FAIL because the candidate UI markers do not exist yet.

- [ ] **Step 3: Add candidate state and selected image derivation**

In `ProductWorkbench`, replace:

```ts
const [result, setResult] = useState<GeneratedImage | null>(null);
```

with:

```ts
const [candidates, setCandidates] = useState<GeneratedImage[]>([]);
const [selectedCandidateIndex, setSelectedCandidateIndex] = useState(0);
const selectedCandidate = candidates[selectedCandidateIndex] ?? null;
```

Replace all `result` checks and `result.src` references with `selectedCandidate`.

In `handleSubmit`, replace:

```ts
setResult(null);
```

with:

```ts
setCandidates([]);
setSelectedCandidateIndex(0);
```

Replace the successful response handling:

```ts
const generatedImage = await submitImageGenerationForm(formData);

setResultSize(size);
setResult(generatedImage);
```

with:

```ts
const generated = await submitImageGenerationForm(formData);

setResultSize(size);
setCandidates(generated.images);
setSelectedCandidateIndex(0);
```

- [ ] **Step 4: Add candidate strip and actions**

Below the selected image preview, add:

```tsx
{candidates.length > 1 && (
  <div className="candidateStrip mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
    {candidates.map((candidate, index) => (
      <button
        key={`${candidate.src}-${index}`}
        type="button"
        onClick={() => setSelectedCandidateIndex(index)}
        disabled={isSubmitting}
        className={classNames(
          "min-w-0 rounded-lg border bg-surface p-2 text-left transition-refined",
          selectedCandidateIndex === index
            ? "border-cyan shadow-soft"
            : "border-border hover:border-cyan",
        )}
      >
        <Image
          unoptimized
          src={candidate.src}
          alt={`方案 ${index + 1}`}
          width={160}
          height={120}
          className="h-20 w-full rounded-md object-cover"
        />
        <span className="mt-2 block text-xs font-semibold text-ink">
          方案 {String.fromCharCode(65 + index)}
        </span>
      </button>
    ))}
  </div>
)}
```

Add action buttons near the current submit button or canvas footer:

```tsx
{selectedCandidate && (
  <div className="mt-3 grid gap-2 sm:grid-cols-2">
    <a
      href={selectedCandidate.src}
      download="product-image.png"
      className="inline-flex min-h-11 items-center justify-center rounded-lg border border-border bg-surface px-4 text-sm font-semibold text-ink transition-refined hover:border-cyan"
    >
      下载图片
    </a>
    <button
      type="button"
      className="inline-flex min-h-11 items-center justify-center rounded-lg border border-cyan bg-accent-soft px-4 text-sm font-semibold text-ink transition-refined hover:bg-cyan hover:text-white"
    >
      继续编辑
    </button>
  </div>
)}
```

- [ ] **Step 5: Run candidate source tests**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/product-workbench.tsx frontend/tests/product-workbench-flow.test.mjs
git commit -m "feat: render generated image candidates"
```

## Task 4: Generation Status Feedback

**Files:**
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/tests/product-workbench-flow.test.mjs`

- [ ] **Step 1: Add failing status expectations**

Append to `frontend/tests/product-workbench-flow.test.mjs`:

```js
test("product workbench exposes staged generation status", () => {
  assert.match(productWorkbenchSource, /generationStatusSteps/);
  assert.match(productWorkbenchSource, /正在校验商品 Brief/);
  assert.match(productWorkbenchSource, /正在组织生成提示/);
  assert.match(productWorkbenchSource, /正在生成候选图片/);
  assert.match(productWorkbenchSource, /正在渲染结果/);
  assert.match(productWorkbenchSource, /statusMessage/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: FAIL because staged status does not exist.

- [ ] **Step 3: Add status state and timer**

Update the React import:

```ts
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
```

Add constants near `imageCountOptions`:

```ts
const generationStatusSteps = [
  "正在校验商品 Brief",
  "正在组织生成提示",
  "正在生成候选图片",
  "正在渲染结果",
] as const;
```

In `ProductWorkbench`, add:

```ts
const [statusStep, setStatusStep] = useState(0);
const statusMessage = isSubmitting
  ? generationStatusSteps[statusStep]
  : selectedCandidate
    ? "已生成候选图，可继续编辑或下载。"
    : "等待生成商品图。";
```

Add effect:

```ts
useEffect(() => {
  if (!isSubmitting) {
    setStatusStep(0);
    return;
  }

  const timer = window.setInterval(() => {
    setStatusStep((currentStep) =>
      Math.min(currentStep + 1, generationStatusSteps.length - 1),
    );
  }, 1800);

  return () => window.clearInterval(timer);
}, [isSubmitting]);
```

- [ ] **Step 4: Render status in the action/status area**

Add this status panel near the submit controls:

```tsx
<div className="rounded-lg border border-cyan/30 bg-cyan/10 px-4 py-3 text-sm leading-6 text-ink">
  <p className="font-semibold text-cyan">系统状态</p>
  <p className="mt-1">{statusMessage}</p>
</div>
```

- [ ] **Step 5: Run tests**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/product-workbench.tsx frontend/tests/product-workbench-flow.test.mjs
git commit -m "feat: show product generation status"
```

## Task 5: Selected Candidate Edit Handoff

**Files:**
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/tests/product-workbench-flow.test.mjs`
- Optionally modify: `frontend/src/lib/agent-api.ts`

- [ ] **Step 1: Add failing handoff expectations**

Append to `frontend/tests/product-workbench-flow.test.mjs`:

```js
test("product workbench can hand selected candidate to agent editing", () => {
  assert.match(productWorkbenchSource, /createAgentSession/);
  assert.match(productWorkbenchSource, /dataUrlToFile/);
  assert.match(productWorkbenchSource, /handleStartEditing/);
  assert.match(productWorkbenchSource, /setEditingSession/);
  assert.match(productWorkbenchSource, /版本历史/);
  assert.match(productWorkbenchSource, /restoreAgentVersion/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: FAIL because the product workbench does not call agent APIs.

- [ ] **Step 3: Import agent helpers and add editing state**

At the top of `frontend/src/components/product-workbench.tsx`, add:

```ts
import {
  createAgentSession,
  restoreAgentVersion,
  sendAgentMessage,
  type AgentEnvelope,
  type AgentImageVersion,
  type AgentMessage,
} from "@/lib/agent-api";
```

Add local aliases and state:

```ts
type AgentSession = AgentEnvelope["session"];

const [editingSession, setEditingSession] = useState<AgentSession | null>(null);
const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
const [currentAgentImage, setCurrentAgentImage] =
  useState<AgentImageVersion | null>(null);
const [agentVersions, setAgentVersions] = useState<AgentImageVersion[]>([]);
```

Add envelope application helper outside the component:

```ts
function applyAgentEnvelope(
  envelope: AgentEnvelope,
  setters: {
    setEditingSession: (session: AgentSession) => void;
    setAgentMessages: (messages: AgentMessage[]) => void;
    setCurrentAgentImage: (image: AgentImageVersion | null) => void;
    setAgentVersions: (versions: AgentImageVersion[]) => void;
  },
) {
  setters.setEditingSession(envelope.session);
  setters.setAgentMessages(envelope.messages);
  setters.setCurrentAgentImage(envelope.currentImage ?? null);
  setters.setAgentVersions(envelope.versions);
}
```

- [ ] **Step 4: Add data URL conversion and start editing**

Add helper outside the component:

```ts
async function dataUrlToFile(src: string, filename: string) {
  const response = await fetch(src);
  const blob = await response.blob();
  return new File([blob], filename, {
    type: blob.type || "image/png",
  });
}
```

Add handler in the component:

```ts
async function handleStartEditing() {
  if (!selectedCandidate || isSubmitting) {
    return;
  }

  setError("");
  setIsSubmitting(true);

  try {
    const formData = new FormData();
    formData.append("instruction", chatInput.trim() || "继续优化这张商品图，保持商品主体一致。");
    formData.append("size", size);
    formData.append(
      "image",
      await dataUrlToFile(selectedCandidate.src, "selected-product.png"),
    );

    const envelope = await createAgentSession(formData);
    applyAgentEnvelope(envelope, {
      setEditingSession,
      setAgentMessages,
      setCurrentAgentImage,
      setAgentVersions,
    });
  } catch (caught) {
    setError(caught instanceof Error ? caught.message : "创建编辑会话失败。");
  } finally {
    setIsSubmitting(false);
  }
}
```

Wire the `继续编辑` button:

```tsx
<button
  type="button"
  onClick={handleStartEditing}
  disabled={!selectedCandidate || isSubmitting}
  className="inline-flex min-h-11 items-center justify-center rounded-lg border border-cyan bg-accent-soft px-4 text-sm font-semibold text-ink transition-refined hover:bg-cyan hover:text-white disabled:opacity-50"
>
  继续编辑
</button>
```

- [ ] **Step 5: Add follow-up edit and restore handlers**

Add:

```ts
async function handleAgentFollowUp() {
  if (!editingSession || !chatInput.trim() || isSubmitting) {
    return;
  }

  setError("");
  setIsSubmitting(true);

  try {
    const envelope = await sendAgentMessage(editingSession.id, chatInput.trim(), size);
    applyAgentEnvelope(envelope, {
      setEditingSession,
      setAgentMessages,
      setCurrentAgentImage,
      setAgentVersions,
    });
    setChatInput("");
  } catch (caught) {
    setError(caught instanceof Error ? caught.message : "编辑请求失败。");
  } finally {
    setIsSubmitting(false);
  }
}

async function handleRestoreAgentVersion(version: AgentImageVersion) {
  if (!editingSession || isSubmitting) {
    return;
  }

  setError("");
  setIsSubmitting(true);

  try {
    const envelope = await restoreAgentVersion(editingSession.id, version.id);
    applyAgentEnvelope(envelope, {
      setEditingSession,
      setAgentMessages,
      setCurrentAgentImage,
      setAgentVersions,
    });
  } catch (caught) {
    setError(caught instanceof Error ? caught.message : "版本恢复失败。");
  } finally {
    setIsSubmitting(false);
  }
}
```

If `editingSession` exists and the user submits with `chatInput`, call `handleAgentFollowUp()` instead of creating a new `/api/images/generate` request.

- [ ] **Step 6: Render version history**

Near the conversation panel, add:

```tsx
{agentVersions.length > 0 && (
  <section className="mt-4 rounded-lg border border-border bg-paper-subtle p-3">
    <h3 className="text-sm font-semibold text-ink">版本历史</h3>
    <div className="mt-3 grid gap-2">
      {agentVersions.map((version, index) => (
        <button
          key={version.id}
          type="button"
          onClick={() => handleRestoreAgentVersion(version)}
          disabled={isSubmitting || editingSession?.currentVersionId === version.id}
          className="grid grid-cols-[3.5rem_minmax(0,1fr)] gap-3 rounded-lg border border-border bg-surface p-2 text-left text-xs text-ink-light transition-refined hover:border-cyan disabled:opacity-50"
        >
          <img
            src={version.src}
            alt={`版本 ${index + 1}`}
            className="h-14 w-14 rounded-md object-cover"
          />
          <span className="min-w-0">
            <span className="block font-semibold text-ink">版本 {index + 1}</span>
            <span className="line-clamp-2">{version.prompt}</span>
          </span>
        </button>
      ))}
    </div>
  </section>
)}
```

Use `currentAgentImage?.src || selectedCandidate?.src` for the main selected preview once editing has started.

- [ ] **Step 7: Run handoff tests**

Run:

```bash
cd frontend
npm test -- product-workbench-flow.test.mjs
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/product-workbench.tsx frontend/tests/product-workbench-flow.test.mjs
git commit -m "feat: connect candidates to agent editing"
```

## Task 6: Copy And Mojibake Cleanup

**Files:**
- Modify: `frontend/src/lib/tools.ts`
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/tools/[toolId]/page.tsx`
- Modify: frontend tests that assert user-facing copy
- Optionally modify backend files with user-facing Chinese error strings

- [ ] **Step 1: Add readable-copy expectations**

In `frontend/tests/homepage-layout.test.mjs`, ensure these assertions exist:

```js
assert.match(pageSource, /图像指挥台/);
assert.match(pageSource, /电商商品图生成/);
assert.match(pageSource, /商品图/);
assert.match(pageSource, /多轮编辑/);
assert.match(productWorkbenchSource, /电商商品图工作台/);
assert.match(productWorkbenchSource, /生成参数/);
assert.match(productWorkbenchSource, /商业图像预览/);
assert.match(productWorkbenchSource, /Agent 对话调整/);
```

Add mojibake guards:

```js
assert.doesNotMatch(pageSource, /�|鍟|鐢|骞|绱|璁/);
assert.doesNotMatch(toolsSource, /�|鍟|鐢|骞|绱|璁/);
assert.doesNotMatch(productWorkbenchSource, /�|鍟|鐢|骞|绱|璁/);
```

- [ ] **Step 2: Run tests to verify they fail if mojibake remains**

Run:

```bash
cd frontend
npm test -- homepage-layout.test.mjs
```

Expected: FAIL while mojibake strings remain in source.

- [ ] **Step 3: Replace frontend user-facing copy**

Use readable Chinese strings in the touched files. Minimum replacements:

```ts
title: "电商商品图工作台",
description: "用平台、用途、商品 Brief 和对话迭代生成适合上架的商品图。",
```

Platform labels:

```ts
"拼多多"
"淘宝/天猫"
"京东"
"小红书"
"抖音电商"
```

Purpose labels:

```ts
"主图"
"白底图"
"场景图"
"促销图"
"详情页首屏"
```

Navigation labels:

```ts
"图像指挥台"
"电商商品图生成"
"商品图"
"多轮编辑"
"素材库"
"设置"
```

Important workbench labels:

```tsx
"可选上传原图"
"电商平台"
"图片类型"
"画面比例"
"生成像素"
"生成数量"
"商业图像预览"
"等待生成商品图"
"调整方向"
"生成商品图"
"发送调整并生成"
```

- [ ] **Step 4: Run readable-copy tests**

Run:

```bash
cd frontend
npm test -- homepage-layout.test.mjs visual-refinement.test.mjs product-workbench-flow.test.mjs
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/tools.ts frontend/src/components/product-workbench.tsx frontend/src/app/page.tsx frontend/src/app/tools/[toolId]/page.tsx frontend/tests
git commit -m "fix: restore readable product workbench copy"
```

## Task 7: End-To-End Verification

**Files:**
- No source changes expected unless verification finds issues.

- [ ] **Step 1: Run backend tests**

Run:

```bash
cd backend
pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests and lint**

Run:

```bash
cd frontend
npm test
npm run lint
npm run build
```

Expected: all commands pass.

- [ ] **Step 3: Start local services**

In one terminal:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

Expected:

- Backend available at `http://127.0.0.1:8000/health`.
- Frontend available at `http://localhost:3000`.

- [ ] **Step 4: Browser verify core flow**

Open `http://localhost:3000`.

Verify:

- Chinese copy is readable.
- Product brief fields are visible.
- Platform, purpose, aspect ratio, size, and count controls are visible.
- Generate button shows staged status while pending.
- Multiple candidates render when the backend returns multiple images.
- Selecting a candidate updates the large preview.
- Download link points at the selected image.
- Continue editing creates an agent session or shows an actionable error without clearing candidates.

- [ ] **Step 5: Commit verification fixes if needed**

If verification required fixes:

```bash
git add frontend backend
git commit -m "fix: polish product image workflow"
```

If no fixes were needed, do not create an empty commit.

## Self-Review

Spec coverage:

- Product brief fields: Task 2.
- Multi-candidate results: Tasks 1 and 3.
- Generation status: Task 4.
- Selected-candidate edit handoff: Task 5.
- Version restore in main flow: Task 5.
- Readable Chinese copy: Task 6.
- Verification: Task 7.

Placeholder scan:

- The plan uses exact file paths, commands, expected results, and concrete code snippets.
- No step says to add unspecified validation, unspecified tests, or later implementation.

Type consistency:

- `GeneratedImage`, `ImageGenerationResult`, `AgentEnvelope`, `AgentImageVersion`, and `AgentMessage` match the existing frontend API helper names.
- `productCategory`, `sellingPoints`, `preserveRequirements`, and `avoidElements` match existing backend `FormData` field names.
- Agent route helpers reuse existing `createAgentSession`, `sendAgentMessage`, and `restoreAgentVersion`.
