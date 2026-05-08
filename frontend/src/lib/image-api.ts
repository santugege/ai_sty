import type { ImageSize } from "@/lib/tools";

export type GeneratedImage = {
  src: string;
  mimeType: string;
  revisedPrompt?: string | null;
};

type ImageGenerationPayload = {
  image?: GeneratedImage;
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
): Promise<GeneratedImage> {
  const response = await fetch(`${apiBaseUrl}/api/images/generate`, {
    method: "POST",
    body: formData,
  });
  const payload = await readImageGenerationPayload(response);

  if (!response.ok || !payload.image) {
    throw new Error(payload.error || genericErrorMessage);
  }

  return payload.image;
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
