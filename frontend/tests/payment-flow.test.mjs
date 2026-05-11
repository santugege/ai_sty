import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

test("payment api helper creates zpay orders with cookie credentials", () => {
  const source = readFileSync("src/lib/payment-api.ts", "utf8");

  assert.match(source, /createZpayOrder/);
  assert.match(source, /\/api\/payments\/zpay\/orders/);
  assert.match(source, /credentials: "include"/);
  assert.match(source, /subject/);
  assert.match(source, /amount/);
  assert.match(source, /payType/);
});

test("billing page exposes subscription zpay purchase flow", () => {
  assert.equal(existsSync("src/app/billing/page.tsx"), true);
  const paymentSource = readFileSync("src/lib/payment-api.ts", "utf8");
  const source = readFileSync("src/app/billing/page.tsx", "utf8");

  assert.match(paymentSource, /createSubscriptionZpayOrder/);
  assert.match(paymentSource, /\/api\/payments\/zpay\/subscription-orders/);
  assert.match(source, /createSubscriptionZpayOrder/);
  assert.match(source, /planId: selectedPlan\.id/);
  assert.doesNotMatch(source, /createZpayOrder/);
  assert.match(source, /AppNav/);
  assert.match(source, /支付宝/);
  assert.match(source, /微信/);
  assert.match(source, /window\.location\.assign/);
  assert.match(source, /if \(envelope\.order\.paymentUrl\)/);
  assert.match(source, /setStatus/);
  assert.match(source, /!isLoadingPlans && !error && backendPlans\.length === 0/);
});

test("zpay return page gives payment status handoff", () => {
  assert.equal(existsSync("src/app/payments/return/page.tsx"), true);
  const source = readFileSync("src/app/payments/return/page.tsx", "utf8");

  assert.match(source, /AppNav/);
  assert.match(source, /支付结果/);
  assert.match(source, /orderNo/);
  assert.match(source, /回到工作台/);
});

test("navigation includes billing entry for authenticated users", () => {
  const source = readFileSync("src/components/app-nav.tsx", "utf8");

  assert.match(source, /href: "\/billing"/);
  assert.match(source, /WalletCards/);
});
