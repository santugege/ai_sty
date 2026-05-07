# Image Toolbox Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js image-generation toolbox that calls OpenAI image models from server-side API routes while keeping `OPENAI_API_KEY` out of the browser.

**Architecture:** The app uses a configuration-driven tool registry for four image tools, shared client form components, and one server API route for validation and OpenAI Images API calls. Unit tests cover tool configuration, request validation, and OpenAI response normalization; production build verifies the Next.js pages and route compile together.

**Tech Stack:** Next.js App Router, TypeScript, Tailwind CSS, OpenAI Node SDK, Vitest, lucide-react.

---

## File Structure

- Create `package.json`: project metadata, scripts, runtime dependencies, and dev dependencies.
- Create `tsconfig.json`: strict TypeScript setup for Next.js.
- Create `next.config.ts`: Next.js configuration.
- Create `postcss.config.mjs`: Tailwind CSS PostCSS integration.
- Create `eslint.config.mjs`: flat ESLint configuration for Next.js and TypeScript.
- Create `vitest.config.ts`: Vitest unit test configuration.
- Create `.gitignore`: ignore dependencies, build output, env files, and test artifacts.
- Create `.env.example`: document required server environment variables.
- Create `src/app/layout.tsx`: root HTML shell and metadata.
- Create `src/app/globals.css`: Tailwind import, theme tokens, and base styles.
- Create `src/app/page.tsx`: toolbox homepage with four feature cards.
- Create `src/app/tools/[toolId]/page.tsx`: dynamic tool page.
- Create `src/components/tool-card.tsx`: reusable homepage card.
- Create `src/components/tool-form.tsx`: client-side form, upload, submit state, result, and errors.
- Create `src/lib/tools.ts`: typed registry for the four tools.
- Create `src/lib/tools.test.ts`: tests for registry behavior.
- Create `src/lib/image-request.ts`: form validation and prompt composition.
- Create `src/lib/image-request.test.ts`: validation tests.
- Create `src/lib/openai-images.ts`: OpenAI Images API wrapper and response normalization.
- Create `src/lib/openai-images.test.ts`: tests for response normalization and prompt forwarding.
- Create `src/app/api/images/generate/route.ts`: server route that validates `FormData` and calls OpenAI.

---

### Task 1: Project Scaffold

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `next.config.ts`
- Create: `postcss.config.mjs`
- Create: `eslint.config.mjs`
- Create: `vitest.config.ts`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/app/layout.tsx`
- Create: `src/app/globals.css`

- [ ] **Step 1: Create the package manifest**

Write `package.json`:

```json
{
  "name": "image-toolbox",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "lucide-react": "latest",
    "next": "latest",
    "openai": "latest",
    "react": "latest",
    "react-dom": "latest"
  },
  "devDependencies": {
    "@eslint/eslintrc": "latest",
    "@tailwindcss/postcss": "latest",
    "@types/node": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "eslint": "latest",
    "eslint-config-next": "latest",
    "tailwindcss": "latest",
    "typescript": "latest",
    "vitest": "latest"
  }
}
```

- [ ] **Step 2: Install dependencies**

Run:

```bash
rtk npm install
```

Expected: `package-lock.json` is created and npm exits with code 0.

- [ ] **Step 3: Create TypeScript and framework config**

Write `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Write `next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
```

Write `postcss.config.mjs`:

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

Write `eslint.config.mjs`:

```js
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
```

Write `vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
    include: ["src/**/*.test.ts"],
  },
});
```

- [ ] **Step 4: Create environment and ignore files**

Write `.gitignore`:

```gitignore
node_modules
.next
out
coverage
.env
.env.local
.env.*.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
```

Write `.env.example`:

```bash
OPENAI_API_KEY=
OPENAI_IMAGE_MODEL=gpt-image-2
```

- [ ] **Step 5: Create the root app shell**

Write `src/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Image Toolbox",
  description: "AI image creation, photo restoration, portraits, and product visuals powered by OpenAI image models.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
```

Write `src/app/globals.css`:

```css
@import "tailwindcss";

:root {
  color-scheme: light;
  --ink: #171717;
  --muted: #646464;
  --paper: #f7f3ea;
  --panel: #fffdf8;
  --line: #ddd5c7;
  --teal: #0f766e;
  --red: #be3b37;
  --blue: #2563eb;
  --gold: #b7791f;
}

* {
  box-sizing: border-box;
}

html {
  min-height: 100%;
  background:
    linear-gradient(135deg, rgba(15, 118, 110, 0.08), transparent 34%),
    linear-gradient(315deg, rgba(190, 59, 55, 0.08), transparent 32%),
    var(--paper);
}

body {
  min-height: 100vh;
  margin: 0;
  color: var(--ink);
  font-family: ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
}

button,
input,
textarea,
select {
  font: inherit;
}

button {
  cursor: pointer;
}

::selection {
  color: white;
  background: var(--teal);
}
```

- [ ] **Step 6: Verify scaffold compiles far enough**

Run:

```bash
rtk npm run test
```

Expected: Vitest reports no test files or exits cleanly after configuration loads. If Vitest exits because no tests exist, continue to Task 2 where the first tests are added.

- [ ] **Step 7: Commit the scaffold**

Run:

```bash
rtk git add package.json package-lock.json tsconfig.json next.config.ts postcss.config.mjs eslint.config.mjs vitest.config.ts .gitignore .env.example src/app/layout.tsx src/app/globals.css
rtk git commit -m "chore: scaffold next image toolbox"
```

Expected: commit succeeds.

---

### Task 2: Tool Registry

**Files:**
- Create: `src/lib/tools.ts`
- Create: `src/lib/tools.test.ts`

- [ ] **Step 1: Write failing registry tests**

Write `src/lib/tools.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { getToolById, imageTools, imageSizes, isImageSize } from "./tools";

describe("image tool registry", () => {
  it("defines the four launch tools in display order", () => {
    expect(imageTools.map((tool) => tool.id)).toEqual([
      "creator",
      "restore",
      "avatar",
      "product",
    ]);
  });

  it("marks text creation as generation and the other tools as edits", () => {
    expect(getToolById("creator")?.mode).toBe("generate");
    expect(getToolById("restore")?.mode).toBe("edit");
    expect(getToolById("avatar")?.mode).toBe("edit");
    expect(getToolById("product")?.mode).toBe("edit");
  });

  it("requires uploads only for restoration and product workflows", () => {
    expect(getToolById("creator")?.imageRequired).toBe(false);
    expect(getToolById("restore")?.imageRequired).toBe(true);
    expect(getToolById("avatar")?.imageRequired).toBe(false);
    expect(getToolById("product")?.imageRequired).toBe(true);
  });

  it("finds known tools and rejects unknown ids", () => {
    expect(getToolById("avatar")?.title).toBe("头像/写真生成");
    expect(getToolById("missing")).toBeUndefined();
  });

  it("accepts only configured image sizes", () => {
    expect(imageSizes).toEqual(["1024x1024", "1536x1024", "1024x1536"]);
    expect(isImageSize("1536x1024")).toBe(true);
    expect(isImageSize("800x800")).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
rtk npm run test -- src/lib/tools.test.ts
```

Expected: FAIL because `src/lib/tools.ts` does not exist.

- [ ] **Step 3: Implement the tool registry**

Write `src/lib/tools.ts`:

```ts
export const imageSizes = ["1024x1024", "1536x1024", "1024x1536"] as const;

export type ImageSize = (typeof imageSizes)[number];
export type ToolId = "creator" | "restore" | "avatar" | "product";
export type ToolMode = "generate" | "edit";
export type ToolIcon = "sparkles" | "wand" | "user" | "package";

export type ImageTool = {
  id: ToolId;
  title: string;
  eyebrow: string;
  description: string;
  mode: ToolMode;
  icon: ToolIcon;
  accent: "teal" | "red" | "blue" | "gold";
  promptLabel: string;
  promptPlaceholder: string;
  promptRequired: boolean;
  imageRequired: boolean;
  imageLabel: string;
  defaultSize: ImageSize;
  sizeOptions: ImageSize[];
  basePrompt: string;
  examples: string[];
};

export const imageTools: ImageTool[] = [
  {
    id: "creator",
    title: "AI 图片创作",
    eyebrow: "Text to image",
    description: "输入画面描述，生成完整原创图片。",
    mode: "generate",
    icon: "sparkles",
    accent: "teal",
    promptLabel: "画面描述",
    promptPlaceholder: "例如：一间清晨阳光里的木质咖啡馆，窗边有绿植，写实摄影风格",
    promptRequired: true,
    imageRequired: false,
    imageLabel: "参考图",
    defaultSize: "1024x1024",
    sizeOptions: [...imageSizes],
    basePrompt:
      "Create a polished, original image that follows the user's visual description. Prioritize clear composition, coherent lighting, and a finished professional look.",
    examples: ["写实摄影", "儿童绘本", "电影海报", "水彩插画"],
  },
  {
    id: "restore",
    title: "老照片修复",
    eyebrow: "Photo restoration",
    description: "修复划痕、褪色、模糊和年代感损伤。",
    mode: "edit",
    icon: "wand",
    accent: "red",
    promptLabel: "修复要求",
    promptPlaceholder: "例如：保留人物五官和年代感，修复划痕，提升清晰度，恢复自然色彩",
    promptRequired: false,
    imageRequired: true,
    imageLabel: "上传旧照片",
    defaultSize: "1024x1024",
    sizeOptions: [...imageSizes],
    basePrompt:
      "Restore the uploaded old photo. Preserve the original identity, pose, clothing, and historical character. Repair scratches, fading, stains, and blur while keeping the result natural.",
    examples: ["黑白上色", "划痕修复", "清晰增强", "褪色恢复"],
  },
  {
    id: "avatar",
    title: "头像/写真生成",
    eyebrow: "Portrait studio",
    description: "用参考图或风格描述生成头像、写真和社媒形象。",
    mode: "edit",
    icon: "user",
    accent: "blue",
    promptLabel: "头像风格",
    promptPlaceholder: "例如：商务头像，深色西装，自然微笑，干净灰色背景，柔和棚拍光",
    promptRequired: true,
    imageRequired: false,
    imageLabel: "上传参考图",
    defaultSize: "1024x1024",
    sizeOptions: ["1024x1024", "1024x1536"],
    basePrompt:
      "Create a refined portrait or avatar. If a reference image is provided, preserve the person's core facial identity while applying the requested style.",
    examples: ["商务头像", "证件照风格", "社媒头像", "电影感写真"],
  },
  {
    id: "product",
    title: "商品图生成",
    eyebrow: "Product visuals",
    description: "为商品换背景、做场景图和电商展示图。",
    mode: "edit",
    icon: "package",
    accent: "gold",
    promptLabel: "商品场景",
    promptPlaceholder: "例如：保留商品外观，放在浅色石材台面上，背景是现代厨房，自然日光",
    promptRequired: false,
    imageRequired: true,
    imageLabel: "上传商品图",
    defaultSize: "1536x1024",
    sizeOptions: [...imageSizes],
    basePrompt:
      "Generate a clean ecommerce product visual from the uploaded product image. Preserve the product shape, color, logo, and important details while changing the scene as requested.",
    examples: ["白底图", "生活方式场景", "节日背景", "电商主图"],
  },
];

export function getToolById(id: string): ImageTool | undefined {
  return imageTools.find((tool) => tool.id === id);
}

export function isImageSize(value: string): value is ImageSize {
  return imageSizes.includes(value as ImageSize);
}
```

- [ ] **Step 4: Run registry tests**

Run:

```bash
rtk npm run test -- src/lib/tools.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit the registry**

Run:

```bash
rtk git add src/lib/tools.ts src/lib/tools.test.ts
rtk git commit -m "feat: add image tool registry"
```

Expected: commit succeeds.

---

### Task 3: Request Validation

**Files:**
- Create: `src/lib/image-request.ts`
- Create: `src/lib/image-request.test.ts`

- [ ] **Step 1: Write failing validation tests**

Write `src/lib/image-request.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import {
  composeToolPrompt,
  MAX_IMAGE_BYTES,
  SUPPORTED_IMAGE_TYPES,
  validateImageFormData,
} from "./image-request";
import { getToolById } from "./tools";

function form(entries: Record<string, string | File | undefined>) {
  const data = new FormData();
  for (const [key, value] of Object.entries(entries)) {
    if (value !== undefined) {
      data.append(key, value);
    }
  }
  return data;
}

function imageFile(type = "image/png", size = 16) {
  return new File([new Uint8Array(size)], "input.png", { type });
}

describe("validateImageFormData", () => {
  it("requires the server API key", () => {
    const result = validateImageFormData(
      form({ toolId: "creator", prompt: "a quiet studio" }),
      {},
    );

    expect(result).toEqual({
      ok: false,
      status: 500,
      error: "服务器未配置 OPENAI_API_KEY。",
    });
  });

  it("rejects an unknown tool id", () => {
    const result = validateImageFormData(
      form({ toolId: "missing", prompt: "a quiet studio" }),
      { OPENAI_API_KEY: "test-key" },
    );

    expect(result).toEqual({
      ok: false,
      status: 400,
      error: "请选择有效的图片工具。",
    });
  });

  it("rejects an empty required prompt", () => {
    const result = validateImageFormData(
      form({ toolId: "creator", prompt: "   " }),
      { OPENAI_API_KEY: "test-key" },
    );

    expect(result).toEqual({
      ok: false,
      status: 400,
      error: "请输入画面描述。",
    });
  });

  it("requires an upload for old photo restoration", () => {
    const result = validateImageFormData(
      form({ toolId: "restore", prompt: "修复划痕" }),
      { OPENAI_API_KEY: "test-key" },
    );

    expect(result).toEqual({
      ok: false,
      status: 400,
      error: "请上传旧照片。",
    });
  });

  it("rejects unsupported file types", () => {
    const result = validateImageFormData(
      form({
        toolId: "restore",
        prompt: "修复划痕",
        image: imageFile("image/gif"),
      }),
      { OPENAI_API_KEY: "test-key" },
    );

    expect(result).toEqual({
      ok: false,
      status: 400,
      error: "图片格式仅支持 PNG、JPG 或 WebP。",
    });
  });

  it("rejects oversized uploads", () => {
    const result = validateImageFormData(
      form({
        toolId: "restore",
        prompt: "修复划痕",
        image: imageFile("image/png", MAX_IMAGE_BYTES + 1),
      }),
      { OPENAI_API_KEY: "test-key" },
    );

    expect(result).toEqual({
      ok: false,
      status: 400,
      error: "图片不能超过 10MB。",
    });
  });

  it("returns a normalized valid request", () => {
    const result = validateImageFormData(
      form({
        toolId: "restore",
        prompt: "修复划痕",
        size: "1536x1024",
        image: imageFile("image/jpeg"),
      }),
      { OPENAI_API_KEY: "test-key" },
    );

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.tool.id).toBe("restore");
      expect(result.value.prompt).toBe("修复划痕");
      expect(result.value.size).toBe("1536x1024");
      expect(result.value.image?.type).toBe("image/jpeg");
    }
  });

  it("falls back to the tool default size for invalid size input", () => {
    const result = validateImageFormData(
      form({ toolId: "creator", prompt: "a quiet studio", size: "800x800" }),
      { OPENAI_API_KEY: "test-key" },
    );

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.size).toBe("1024x1024");
    }
  });
});

describe("composeToolPrompt", () => {
  it("combines the base prompt with user instructions", () => {
    const tool = getToolById("product");
    expect(tool).toBeDefined();

    const prompt = composeToolPrompt(tool!, "放在现代厨房里");

    expect(prompt).toContain(tool!.basePrompt);
    expect(prompt).toContain("User request:");
    expect(prompt).toContain("放在现代厨房里");
  });

  it("uses the base prompt when optional user instructions are empty", () => {
    const tool = getToolById("restore");
    expect(tool).toBeDefined();

    expect(composeToolPrompt(tool!, "   ")).toBe(tool!.basePrompt);
  });

  it("documents supported upload types", () => {
    expect(SUPPORTED_IMAGE_TYPES).toEqual([
      "image/png",
      "image/jpeg",
      "image/webp",
    ]);
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
rtk npm run test -- src/lib/image-request.test.ts
```

Expected: FAIL because `src/lib/image-request.ts` does not exist.

- [ ] **Step 3: Implement validation and prompt composition**

Write `src/lib/image-request.ts`:

```ts
import { getToolById, isImageSize, type ImageSize, type ImageTool } from "./tools";

export const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
export const SUPPORTED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"] as const;

export type SupportedImageType = (typeof SUPPORTED_IMAGE_TYPES)[number];

export type ValidImageRequest = {
  tool: ImageTool;
  prompt: string;
  size: ImageSize;
  image?: File;
};

export type ValidationResult =
  | {
      ok: true;
      value: ValidImageRequest;
    }
  | {
      ok: false;
      status: number;
      error: string;
    };

type EnvLike = {
  OPENAI_API_KEY?: string;
};

export function validateImageFormData(
  formData: FormData,
  env: EnvLike = process.env,
): ValidationResult {
  if (!env.OPENAI_API_KEY) {
    return {
      ok: false,
      status: 500,
      error: "服务器未配置 OPENAI_API_KEY。",
    };
  }

  const toolId = readString(formData, "toolId");
  const tool = toolId ? getToolById(toolId) : undefined;

  if (!tool) {
    return {
      ok: false,
      status: 400,
      error: "请选择有效的图片工具。",
    };
  }

  const prompt = readString(formData, "prompt").trim();

  if (tool.promptRequired && !prompt) {
    return {
      ok: false,
      status: 400,
      error: `请输入${tool.promptLabel}。`,
    };
  }

  const upload = readFile(formData, "image");

  if (tool.imageRequired && !upload) {
    return {
      ok: false,
      status: 400,
      error: `请${tool.imageLabel}。`,
    };
  }

  if (upload && !isSupportedImageType(upload.type)) {
    return {
      ok: false,
      status: 400,
      error: "图片格式仅支持 PNG、JPG 或 WebP。",
    };
  }

  if (upload && upload.size > MAX_IMAGE_BYTES) {
    return {
      ok: false,
      status: 400,
      error: "图片不能超过 10MB。",
    };
  }

  const requestedSize = readString(formData, "size");
  const size = isImageSize(requestedSize) && tool.sizeOptions.includes(requestedSize)
    ? requestedSize
    : tool.defaultSize;

  return {
    ok: true,
    value: {
      tool,
      prompt,
      size,
      ...(upload ? { image: upload } : {}),
    },
  };
}

export function composeToolPrompt(tool: ImageTool, userPrompt: string) {
  const trimmed = userPrompt.trim();

  if (!trimmed) {
    return tool.basePrompt;
  }

  return `${tool.basePrompt}\n\nUser request:\n${trimmed}`;
}

function readString(formData: FormData, key: string) {
  const value = formData.get(key);
  return typeof value === "string" ? value : "";
}

function readFile(formData: FormData, key: string) {
  const value = formData.get(key);

  if (value instanceof File && value.size > 0) {
    return value;
  }

  return undefined;
}

function isSupportedImageType(type: string): type is SupportedImageType {
  return SUPPORTED_IMAGE_TYPES.includes(type as SupportedImageType);
}
```

- [ ] **Step 4: Run validation tests**

Run:

```bash
rtk npm run test -- src/lib/image-request.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit validation**

Run:

```bash
rtk git add src/lib/image-request.ts src/lib/image-request.test.ts
rtk git commit -m "feat: validate image generation requests"
```

Expected: commit succeeds.

---

### Task 4: OpenAI Images API Wrapper and Route

**Files:**
- Create: `src/lib/openai-images.ts`
- Create: `src/lib/openai-images.test.ts`
- Create: `src/app/api/images/generate/route.ts`

- [ ] **Step 1: Write failing OpenAI wrapper tests**

Write `src/lib/openai-images.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { normalizeOpenAIImageResponse } from "./openai-images";

describe("normalizeOpenAIImageResponse", () => {
  it("returns a png data URL when the API returns base64 image data", () => {
    const result = normalizeOpenAIImageResponse({
      data: [{ b64_json: "abc123", revised_prompt: "a refined prompt" }],
    });

    expect(result).toEqual({
      src: "data:image/png;base64,abc123",
      mimeType: "image/png",
      revisedPrompt: "a refined prompt",
    });
  });

  it("returns an API URL when the API returns a hosted URL", () => {
    const result = normalizeOpenAIImageResponse({
      data: [{ url: "https://example.test/image.png" }],
    });

    expect(result).toEqual({
      src: "https://example.test/image.png",
      mimeType: "image/png",
      revisedPrompt: undefined,
    });
  });

  it("throws a stable error when no image is returned", () => {
    expect(() => normalizeOpenAIImageResponse({ data: [] })).toThrow(
      "OpenAI 没有返回图片结果。",
    );
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
rtk npm run test -- src/lib/openai-images.test.ts
```

Expected: FAIL because `src/lib/openai-images.ts` does not exist.

- [ ] **Step 3: Implement the OpenAI wrapper**

Write `src/lib/openai-images.ts`:

```ts
import OpenAI, { toFile } from "openai";
import { composeToolPrompt, type ValidImageRequest } from "./image-request";

export type GeneratedImageResult = {
  src: string;
  mimeType: "image/png";
  revisedPrompt?: string;
};

type ImageResponseLike = {
  data?: Array<{
    b64_json?: string | null;
    url?: string | null;
    revised_prompt?: string | null;
  }>;
};

export async function requestImageFromOpenAI(
  request: ValidImageRequest,
  apiKey: string,
): Promise<GeneratedImageResult> {
  const client = new OpenAI({ apiKey });
  const prompt = composeToolPrompt(request.tool, request.prompt);
  const model = process.env.OPENAI_IMAGE_MODEL || "gpt-image-2";

  if (request.tool.mode === "generate") {
    const response = await client.images.generate({
      model,
      prompt,
      size: request.size,
      quality: "auto",
    });

    return normalizeOpenAIImageResponse(response);
  }

  if (!request.image) {
    throw new Error("该工具需要上传图片。");
  }

  const image = await browserFileToOpenAIFile(request.image);
  const response = await client.images.edit({
    model,
    image,
    prompt,
    size: request.size,
    quality: "auto",
  });

  return normalizeOpenAIImageResponse(response);
}

export function normalizeOpenAIImageResponse(
  response: ImageResponseLike,
): GeneratedImageResult {
  const image = response.data?.[0];

  if (image?.b64_json) {
    return {
      src: `data:image/png;base64,${image.b64_json}`,
      mimeType: "image/png",
      revisedPrompt: image.revised_prompt ?? undefined,
    };
  }

  if (image?.url) {
    return {
      src: image.url,
      mimeType: "image/png",
      revisedPrompt: image.revised_prompt ?? undefined,
    };
  }

  throw new Error("OpenAI 没有返回图片结果。");
}

async function browserFileToOpenAIFile(file: File) {
  const buffer = Buffer.from(await file.arrayBuffer());
  return toFile(buffer, file.name || "input.png", {
    type: file.type || "image/png",
  });
}
```

- [ ] **Step 4: Run OpenAI wrapper tests**

Run:

```bash
rtk npm run test -- src/lib/openai-images.test.ts
```

Expected: PASS.

- [ ] **Step 5: Create the API route**

Write `src/app/api/images/generate/route.ts`:

```ts
import { NextResponse } from "next/server";
import { validateImageFormData } from "@/lib/image-request";
import { requestImageFromOpenAI } from "@/lib/openai-images";

export const runtime = "nodejs";

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const validation = validateImageFormData(formData);

    if (!validation.ok) {
      return NextResponse.json(
        { error: validation.error },
        { status: validation.status },
      );
    }

    const image = await requestImageFromOpenAI(
      validation.value,
      process.env.OPENAI_API_KEY!,
    );

    return NextResponse.json({ image });
  } catch (error) {
    console.error("Image generation failed", error);

    return NextResponse.json(
      { error: getPublicErrorMessage(error) },
      { status: 502 },
    );
  }
}

function getPublicErrorMessage(error: unknown) {
  if (error instanceof Error && /content policy|safety/i.test(error.message)) {
    return "请求未通过图片安全审核，请调整描述后重试。";
  }

  if (error instanceof Error && error.message === "OpenAI 没有返回图片结果。") {
    return error.message;
  }

  return "图片生成失败，请稍后重试。";
}
```

- [ ] **Step 6: Run all unit tests**

Run:

```bash
rtk npm run test
```

Expected: PASS for registry, validation, and OpenAI wrapper tests.

- [ ] **Step 7: Commit server integration**

Run:

```bash
rtk git add src/lib/openai-images.ts src/lib/openai-images.test.ts src/app/api/images/generate/route.ts
rtk git commit -m "feat: add openai image generation api"
```

Expected: commit succeeds.

---

### Task 5: Toolbox Frontend

**Files:**
- Create: `src/components/tool-card.tsx`
- Create: `src/components/tool-form.tsx`
- Create: `src/app/page.tsx`
- Create: `src/app/tools/[toolId]/page.tsx`

- [ ] **Step 1: Create reusable tool cards**

Write `src/components/tool-card.tsx`:

```tsx
import Link from "next/link";
import { PackageSearch, Sparkles, UserRound, Wand2 } from "lucide-react";
import type { ImageTool } from "@/lib/tools";

const iconMap = {
  sparkles: Sparkles,
  wand: Wand2,
  user: UserRound,
  package: PackageSearch,
};

const accentClasses = {
  teal: "border-teal-700/25 bg-teal-700/8 text-teal-900",
  red: "border-red-700/25 bg-red-700/8 text-red-900",
  blue: "border-blue-700/25 bg-blue-700/8 text-blue-900",
  gold: "border-amber-700/30 bg-amber-700/10 text-amber-950",
};

export function ToolCard({ tool }: { tool: ImageTool }) {
  const Icon = iconMap[tool.icon];

  return (
    <Link
      href={`/tools/${tool.id}`}
      className="group grid min-h-64 content-between rounded-lg border border-stone-300 bg-white/75 p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-stone-950 hover:shadow-xl"
    >
      <div>
        <div
          className={`mb-5 inline-flex h-12 w-12 items-center justify-center rounded-md border ${accentClasses[tool.accent]}`}
        >
          <Icon aria-hidden="true" className="h-6 w-6" />
        </div>
        <p className="text-sm uppercase tracking-[0.18em] text-stone-500">
          {tool.eyebrow}
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-tight text-stone-950">
          {tool.title}
        </h2>
        <p className="mt-4 text-base leading-7 text-stone-600">
          {tool.description}
        </p>
      </div>
      <div className="mt-8 flex flex-wrap gap-2">
        {tool.examples.map((example) => (
          <span
            key={example}
            className="rounded border border-stone-300 px-2.5 py-1 text-sm text-stone-600"
          >
            {example}
          </span>
        ))}
      </div>
    </Link>
  );
}
```

- [ ] **Step 2: Create the client tool form**

Write `src/components/tool-form.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import { AlertCircle, ImageIcon, Loader2, Upload } from "lucide-react";
import type { ImageTool } from "@/lib/tools";

type GeneratedImage = {
  src: string;
  mimeType: string;
  revisedPrompt?: string;
};

type ToolFormProps = {
  tool: ImageTool;
};

export function ToolForm({ tool }: ToolFormProps) {
  const [prompt, setPrompt] = useState("");
  const [size, setSize] = useState(tool.defaultSize);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<GeneratedImage | null>(null);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fileLabel = useMemo(() => {
    if (!file) {
      return tool.imageRequired ? "请选择图片文件" : "可选上传参考图";
    }

    return file.name;
  }, [file, tool.imageRequired]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setResult(null);
    setIsSubmitting(true);

    const formData = new FormData();
    formData.append("toolId", tool.id);
    formData.append("prompt", prompt);
    formData.append("size", size);

    if (file) {
      formData.append("image", file);
    }

    try {
      const response = await fetch("/api/images/generate", {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as {
        image?: GeneratedImage;
        error?: string;
      };

      if (!response.ok || !payload.image) {
        throw new Error(payload.error || "图片生成失败，请稍后重试。");
      }

      setResult(payload.image);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "图片生成失败，请稍后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-stone-300 bg-white/80 p-5 shadow-sm"
      >
        <label className="block text-sm font-semibold text-stone-900">
          {tool.promptLabel}
        </label>
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder={tool.promptPlaceholder}
          rows={7}
          className="mt-3 w-full resize-none rounded-md border border-stone-300 bg-white px-4 py-3 text-base leading-7 text-stone-950 outline-none transition focus:border-stone-950"
        />

        {(tool.imageRequired || tool.mode === "edit") && (
          <label className="mt-5 block">
            <span className="text-sm font-semibold text-stone-900">
              {tool.imageLabel}
            </span>
            <span className="mt-3 flex min-h-28 items-center gap-3 rounded-md border border-dashed border-stone-400 bg-stone-50 px-4 py-4 text-stone-600 transition hover:border-stone-950">
              <Upload aria-hidden="true" className="h-5 w-5 shrink-0" />
              <span className="min-w-0 truncate">{fileLabel}</span>
            </span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>
        )}

        <label className="mt-5 block text-sm font-semibold text-stone-900">
          输出尺寸
        </label>
        <select
          value={size}
          onChange={(event) => setSize(event.target.value as typeof size)}
          className="mt-3 w-full rounded-md border border-stone-300 bg-white px-4 py-3 text-stone-950 outline-none transition focus:border-stone-950"
        >
          {tool.sizeOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>

        {error && (
          <div className="mt-5 flex gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-800">
            <AlertCircle aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="mt-6 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-md bg-stone-950 px-5 py-3 text-base font-semibold text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:bg-stone-500"
        >
          {isSubmitting ? (
            <Loader2 aria-hidden="true" className="h-5 w-5 animate-spin" />
          ) : (
            <ImageIcon aria-hidden="true" className="h-5 w-5" />
          )}
          {isSubmitting ? "生成中" : "生成图片"}
        </button>
      </form>

      <section className="grid min-h-[34rem] place-items-center rounded-lg border border-stone-300 bg-stone-950 p-4 text-white shadow-sm">
        {result ? (
          <div className="w-full">
            <img
              src={result.src}
              alt={`${tool.title}生成结果`}
              className="mx-auto max-h-[32rem] w-auto max-w-full rounded-md object-contain"
            />
            {result.revisedPrompt && (
              <p className="mt-4 text-sm leading-6 text-stone-300">
                {result.revisedPrompt}
              </p>
            )}
          </div>
        ) : (
          <div className="max-w-sm text-center">
            <ImageIcon aria-hidden="true" className="mx-auto h-10 w-10 text-stone-400" />
            <p className="mt-4 text-xl font-semibold">结果会显示在这里</p>
            <p className="mt-3 text-sm leading-6 text-stone-400">
              提交后请等待图片模型完成生成，复杂图片可能需要较长时间。
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 3: Create the toolbox homepage**

Write `src/app/page.tsx`:

```tsx
import { ToolCard } from "@/components/tool-card";
import { imageTools } from "@/lib/tools";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-8 sm:px-8 lg:px-10">
      <header className="grid gap-6 border-b border-stone-300 pb-8 lg:grid-cols-[1fr_0.75fr] lg:items-end">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-stone-500">
            OpenAI image studio
          </p>
          <h1 className="mt-4 max-w-4xl text-5xl font-semibold leading-[1.04] text-stone-950 sm:text-6xl lg:text-7xl">
            图片生成工具箱
          </h1>
        </div>
        <p className="max-w-xl text-lg leading-8 text-stone-600">
          选择一个功能，输入描述或上传图片，由服务器安全调用 OpenAI 图片模型生成结果。
        </p>
      </header>

      <section className="grid flex-1 gap-4 py-8 sm:grid-cols-2 xl:grid-cols-4">
        {imageTools.map((tool) => (
          <ToolCard key={tool.id} tool={tool} />
        ))}
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Create dynamic tool pages**

Write `src/app/tools/[toolId]/page.tsx`:

```tsx
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { notFound } from "next/navigation";
import { ToolForm } from "@/components/tool-form";
import { getToolById, imageTools } from "@/lib/tools";

type ToolPageProps = {
  params: Promise<{
    toolId: string;
  }>;
};

export function generateStaticParams() {
  return imageTools.map((tool) => ({
    toolId: tool.id,
  }));
}

export async function generateMetadata({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  return {
    title: tool ? `${tool.title} | Image Toolbox` : "Image Toolbox",
  };
}

export default async function ToolPage({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  if (!tool) {
    notFound();
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm font-semibold text-stone-600 transition hover:text-stone-950"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        返回工具箱
      </Link>

      <header className="mt-8 grid gap-5 border-b border-stone-300 pb-8 lg:grid-cols-[1fr_0.72fr] lg:items-end">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-stone-500">
            {tool.eyebrow}
          </p>
          <h1 className="mt-4 text-5xl font-semibold leading-tight text-stone-950">
            {tool.title}
          </h1>
        </div>
        <p className="max-w-xl text-lg leading-8 text-stone-600">
          {tool.description}
        </p>
      </header>

      <section className="py-8">
        <ToolForm tool={tool} />
      </section>
    </main>
  );
}
```

- [ ] **Step 5: Run frontend build**

Run:

```bash
rtk npm run build
```

Expected: PASS. The build lists `/`, `/tools/[toolId]`, and `/api/images/generate`.

- [ ] **Step 6: Commit frontend**

Run:

```bash
rtk git add src/components/tool-card.tsx src/components/tool-form.tsx src/app/page.tsx src/app/tools/[toolId]/page.tsx
rtk git commit -m "feat: build image toolbox frontend"
```

Expected: commit succeeds.

---

### Task 6: Final Verification and Local Run

**Files:**
- Modify only if verification reveals a concrete defect in files from earlier tasks.

- [ ] **Step 1: Run the complete automated check suite**

Run:

```bash
rtk npm run test
rtk npm run lint
rtk npm run build
```

Expected: all commands exit with code 0.

- [ ] **Step 2: Verify missing API key behavior**

Run:

```bash
rtk npm run dev
```

Open `http://localhost:3000`, choose `AI 图片创作`, submit a prompt without creating `.env.local`.

Expected: the page displays `服务器未配置 OPENAI_API_KEY。`.

- [ ] **Step 3: Verify request validation in the browser**

With the dev server still running:

- Open `http://localhost:3000/tools/creator`, submit an empty prompt.
- Open `http://localhost:3000/tools/restore`, submit without an upload.
- Open `http://localhost:3000/tools/restore`, upload a GIF file.

Expected:

- Empty creator prompt displays `请输入画面描述。`.
- Missing restoration upload displays `请上传旧照片。`.
- GIF upload displays `图片格式仅支持 PNG、JPG 或 WebP。`.

- [ ] **Step 4: Verify one real OpenAI image request**

Create `.env.local` with:

```bash
OPENAI_API_KEY=replace-with-real-key
OPENAI_IMAGE_MODEL=gpt-image-2
```

Restart the dev server:

```bash
rtk npm run dev
```

Open `http://localhost:3000/tools/creator`, submit:

```text
一张产品级网页配图：玻璃桌面上的复古相机，清晨自然光，浅景深，真实摄影风格
```

Expected: the result panel displays a generated image.

- [ ] **Step 5: Commit verification fixes if any were needed**

If files changed during verification, run:

```bash
rtk git status --short
rtk git add <changed-files>
rtk git commit -m "fix: polish image toolbox verification issues"
```

Expected: commit succeeds when there are changes. If no files changed, skip the commit.

---

## Self-Review

Spec coverage:

- Toolbox homepage with four feature cards: Task 5.
- Separate configurable tool pages: Tasks 2 and 5.
- Server-side `OPENAI_API_KEY`: Tasks 1, 3, 4, and 6.
- OpenAI Images API integration: Task 4.
- Text generation and image editing flows: Tasks 2, 3, 4, and 5.
- User-facing validation and errors: Tasks 3, 4, 5, and 6.
- Build and real API verification: Task 6.

Placeholder scan:

- The plan contains no unfinished placeholder steps.
- Every file creation step includes concrete content.
- Every verification step includes exact commands and expected results.

Type consistency:

- `ToolId`, `ImageTool`, `ImageSize`, and `ValidImageRequest` are defined before use.
- `validateImageFormData` returns the value consumed by `requestImageFromOpenAI`.
- The API route returns the `GeneratedImageResult` shape consumed by `ToolForm`.

