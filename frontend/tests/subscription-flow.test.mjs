import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

test("subscription api exposes user and admin plan helpers with cookie credentials", () => {
  assert.equal(existsSync("src/lib/subscription-api.ts"), true);
  const source = readFileSync("src/lib/subscription-api.ts", "utf8");

  assert.match(source, /listSubscriptionPlans/);
  assert.match(source, /getMyEntitlement/);
  assert.match(source, /listAdminSubscriptionPlans/);
  assert.match(source, /createAdminSubscriptionPlan/);
  assert.match(source, /credentials: "include"/);
  assert.match(source, /\/api\/subscription\/plans/);
  assert.match(source, /\/api\/admin\/subscription\/plans/);
});

test("payment api exposes subscription zpay orders with plan ids", () => {
  const source = readFileSync("src/lib/payment-api.ts", "utf8");

  assert.match(source, /CreateSubscriptionZpayOrderInput/);
  assert.match(source, /createSubscriptionZpayOrder/);
  assert.match(source, /\/api\/payments\/zpay\/subscription-orders/);
  assert.match(source, /planId/);
  assert.match(source, /credentials: "include"/);
});

test("billing page loads backend subscription plans and creates subscription orders", () => {
  assert.equal(existsSync("src/app/billing/page.tsx"), true);
  const source = readFileSync("src/app/billing/page.tsx", "utf8");

  assert.match(source, /listSubscriptionPlans/);
  assert.match(source, /createSubscriptionZpayOrder/);
  assert.doesNotMatch(source, /const plans = \[/);
  assert.match(source, /每日/);
  assert.match(source, /每月/);
  assert.match(source, /planId: selectedPlan\.id/);
  assert.match(source, /window\.location\.assign/);
});

test("admin subscription page manages plan fields", () => {
  const source = readFileSync("src/app/admin/subscriptions/page.tsx", "utf8");

  assert.match(source, /listAdminSubscriptionPlans/);
  assert.match(source, /createAdminSubscriptionPlan/);
  assert.match(source, /dailyImageLimit/);
  assert.match(source, /monthlyImageLimit/);
  assert.match(source, /每日额度/);
  assert.match(source, /每月额度/);
});

test("navigation links admin subscription management for admins", () => {
  const source = readFileSync("src/components/app-nav.tsx", "utf8");

  assert.match(source, /href: "\/admin\/subscriptions"/);
  assert.match(source, /订阅管理/);
});

test("image api preserves subscription limit payload", () => {
  const source = readFileSync("src/lib/image-api.ts", "utf8");

  assert.match(source, /SUBSCRIPTION_LIMIT_REACHED/);
  assert.match(source, /SubscriptionLimitError/);
  assert.match(source, /usage/);
  assert.match(source, /plans/);
});

test("product workbench opens subscription modal on quota limit", () => {
  const source = readFileSync("src/components/product-workbench.tsx", "utf8");

  assert.match(source, /subscriptionLimit/);
  assert.match(source, /SUBSCRIPTION_LIMIT_REACHED/);
  assert.match(source, /套餐额度不足/);
  assert.match(source, /\/billing/);
});
