const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type SubscriptionPlan = {
  id: string;
  code: string;
  name: string;
  description: string;
  price: string;
  dailyImageLimit: number;
  monthlyImageLimit: number;
  isActive: boolean;
  isDefault: boolean;
  sortOrder: number;
};

export type Entitlement = {
  plan: SubscriptionPlan;
  dailyLimit: number;
  monthlyLimit: number;
  todayUsed: number;
  monthUsed: number;
  dailyRemaining: number;
  monthlyRemaining: number;
};

export type PlanInput = {
  code?: string;
  name: string;
  description: string;
  price: string;
  dailyImageLimit: number;
  monthlyImageLimit: number;
  isActive: boolean;
  isDefault: boolean;
  sortOrder: number;
};

export type SubscriptionPlanListEnvelope = {
  plans: SubscriptionPlan[];
};

export type EntitlementEnvelope = {
  entitlement: Entitlement;
};

export type SubscriptionPlanEnvelope = {
  plan: SubscriptionPlan;
};

export async function listSubscriptionPlans(): Promise<SubscriptionPlanListEnvelope> {
  return readJsonResponse<SubscriptionPlanListEnvelope>(
    await fetch(`${apiBaseUrl}/api/subscription/plans`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function getMyEntitlement(): Promise<EntitlementEnvelope> {
  return readJsonResponse<EntitlementEnvelope>(
    await fetch(`${apiBaseUrl}/api/subscription/me`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function listAdminSubscriptionPlans(): Promise<SubscriptionPlanListEnvelope> {
  return readJsonResponse<SubscriptionPlanListEnvelope>(
    await fetch(`${apiBaseUrl}/api/admin/subscription/plans`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function createAdminSubscriptionPlan(
  input: PlanInput,
): Promise<SubscriptionPlanEnvelope> {
  return readJsonResponse<SubscriptionPlanEnvelope>(
    await fetch(`${apiBaseUrl}/api/admin/subscription/plans`, {
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
    throw new Error(payload.error || payload.detail || "Subscription request failed.");
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
