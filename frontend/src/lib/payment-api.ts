const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type CreateZpayOrderInput = {
  subject: string;
  amount: string;
  payType: "alipay" | "wxpay";
};

export type CreateSubscriptionZpayOrderInput = {
  planId: string;
  payType: "alipay" | "wxpay";
};

export type PaymentOrder = {
  id: string;
  orderNo: string;
  subject: string;
  amount: string;
  payType: string;
  provider: string;
  status: string;
  paymentUrl: string | null;
  createdAt: string;
  paidAt: string | null;
};

export type PaymentOrderEnvelope = {
  order: PaymentOrder;
};

export async function createZpayOrder(
  input: CreateZpayOrderInput,
): Promise<PaymentOrderEnvelope> {
  return readJsonResponse<PaymentOrderEnvelope>(
    await fetch(`${apiBaseUrl}/api/payments/zpay/orders`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

export async function createSubscriptionZpayOrder(
  input: CreateSubscriptionZpayOrderInput,
): Promise<PaymentOrderEnvelope> {
  return readJsonResponse<PaymentOrderEnvelope>(
    await fetch(`${apiBaseUrl}/api/payments/zpay/subscription-orders`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

async function readJsonResponse<T>(response: Response): Promise<T> {
  const payload = await readJsonPayload<T>(response);
  if (!response.ok || payload.error || payload.detail) {
    throw new Error(payload.error || payload.detail || "Payment request failed.");
  }
  return payload;
}

async function readJsonPayload<T>(
  response: Response,
): Promise<T & { error?: string | null; detail?: string | null }> {
  const contentType = response.headers.get("content-type")?.toLowerCase();

  if (!contentType?.includes("json")) {
    return {} as T & { error?: string | null; detail?: string | null };
  }

  try {
    return (await response.json()) as T & {
      error?: string | null;
      detail?: string | null;
    };
  } catch {
    return {} as T & { error?: string | null; detail?: string | null };
  }
}
