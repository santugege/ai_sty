import type { ImageSize } from "@/lib/tools";

export type GeneratedImage = {
  src: string;
  mimeType: string;
  revisedPrompt?: string | null;
};

export type SubscriptionLimitPayload = {
  error: string;
  errorCode: "SUBSCRIPTION_LIMIT_REACHED";
  usage: {
    plan: {
      name: string;
    };
    dailyRemaining: number;
    monthlyRemaining: number;
  };
  plans: Array<{
    id: string;
    name: string;
    price: string;
    dailyImageLimit: number;
    monthlyImageLimit: number;
  }>;
};

export class SubscriptionLimitError extends Error {
  payload: SubscriptionLimitPayload;

  constructor(payload: SubscriptionLimitPayload) {
    super(payload.error);
    this.name = "SubscriptionLimitError";
    this.payload = payload;
  }
}

type ImageGenerationPayload = {
  image?: GeneratedImage;
  error?: string;
  errorCode?: string;
  detail?: string;
  usage?: SubscriptionLimitPayload["usage"];
  plans?: SubscriptionLimitPayload["plans"];
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
    credentials: "include",
    body: formData,
  });
  const payload = await readImageGenerationPayload(response);

  if (!response.ok || !payload.image) {
    if (payload.errorCode === "SUBSCRIPTION_LIMIT_REACHED") {
      throw new SubscriptionLimitError(payload as SubscriptionLimitPayload);
    }
    throw new Error(payload.error || payload.detail || genericErrorMessage);
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
