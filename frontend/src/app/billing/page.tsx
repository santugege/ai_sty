"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Loader2, WalletCards } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import {
  createSubscriptionZpayOrder,
  type CreateSubscriptionZpayOrderInput,
} from "@/lib/payment-api";
import {
  listSubscriptionPlans,
  type SubscriptionPlan,
} from "@/lib/subscription-api";

const payTypes: Array<{
  label: string;
  value: CreateSubscriptionZpayOrderInput["payType"];
}> = [
  { label: "支付宝", value: "alipay" },
  { label: "微信", value: "wxpay" },
];

export default function BillingPage() {
  const [backendPlans, setBackendPlans] = useState<SubscriptionPlan[]>([]);
  const [planId, setPlanId] = useState("");
  const [payType, setPayType] =
    useState<CreateSubscriptionZpayOrderInput["payType"]>("alipay");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [isLoadingPlans, setIsLoadingPlans] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadPlans() {
      setError("");
      setIsLoadingPlans(true);

      try {
        const envelope = await listSubscriptionPlans();
        if (!active) {
          return;
        }

        setBackendPlans(envelope.plans);
        setPlanId((currentPlanId) => currentPlanId || envelope.plans[0]?.id || "");
      } catch (caught) {
        if (active) {
          setError(caught instanceof Error ? caught.message : "套餐加载失败。");
        }
      } finally {
        if (active) {
          setIsLoadingPlans(false);
        }
      }
    }

    void loadPlans();

    return () => {
      active = false;
    };
  }, []);

  const selectedPlan = useMemo(
    () =>
      backendPlans.find((plan) => plan.id === planId) ||
      backendPlans[0] ||
      null,
    [backendPlans, planId],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setStatus("");

    if (!selectedPlan) {
      setError("请选择可用套餐。");
      return;
    }

    setIsSubmitting(true);

    try {
      const envelope = await createSubscriptionZpayOrder({
        planId: selectedPlan.id,
        payType,
      });

      if (envelope.order.paymentUrl) {
        window.location.assign(envelope.order.paymentUrl);
        return;
      }

      setStatus("套餐已生效。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "订阅订单创建失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppShell fit="page">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
            <section className="min-w-0">
              <p className="text-xs font-bold uppercase text-accent">Billing</p>
              <h1 className="mt-1 text-2xl font-black">订阅套餐</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-light">
                选择一个后端配置的订阅套餐。付费套餐会跳转到 ZPAY 收银台，免费套餐会直接生效。
              </p>

              <form onSubmit={(event) => void handleSubmit(event)} className="mt-5 grid gap-4">
                <fieldset className="grid gap-3 sm:grid-cols-2">
                  <legend className="sr-only">订阅套餐</legend>
                  {isLoadingPlans ? (
                    <div className="rounded-lg border border-border bg-surface p-4 text-sm font-medium text-ink-light">
                      正在加载套餐...
                    </div>
                  ) : null}

                  {!isLoadingPlans && !error && backendPlans.length === 0 ? (
                    <div className="rounded-lg border border-border bg-surface p-4 text-sm font-medium text-ink-light">
                      暂无可用套餐。
                    </div>
                  ) : null}

                  {backendPlans.map((plan) => {
                    const active = plan.id === selectedPlan?.id;

                    return (
                      <label
                        key={plan.id}
                        className={`rounded-lg border p-4 transition-refined ${
                          active
                            ? "border-accent bg-accent-soft"
                            : "border-border bg-surface hover:border-border-hover"
                        }`}
                      >
                        <input
                          type="radio"
                          name="plan"
                          value={plan.id}
                          checked={active}
                          onChange={() => setPlanId(plan.id)}
                          className="sr-only"
                        />
                        <span className="block text-sm font-black">{plan.name}</span>
                        <span className="mt-2 block text-2xl font-black">
                          ¥{plan.price}
                        </span>
                        <span className="mt-2 block text-sm leading-6 text-ink-light">
                          {plan.description || "订阅图片生成额度"}
                        </span>
                        <span className="mt-3 block text-xs font-bold text-ink-light">
                          每日 {plan.dailyImageLimit} 张 / 每月 {plan.monthlyImageLimit} 张
                        </span>
                      </label>
                    );
                  })}
                </fieldset>

                <fieldset className="rounded-lg border border-border bg-surface p-4">
                  <legend className="mb-3 text-sm font-black">支付方式</legend>
                  <div className="flex flex-wrap gap-2">
                    {payTypes.map((option) => {
                      const active = payType === option.value;

                      return (
                        <label
                          key={option.value}
                          className={`inline-flex h-10 items-center rounded-md border px-4 text-sm font-bold transition-refined ${
                            active
                              ? "border-ink bg-ink text-white"
                              : "border-border bg-surface text-ink-light hover:border-border-hover hover:text-ink"
                          }`}
                        >
                          <input
                            type="radio"
                            name="payType"
                            value={option.value}
                            checked={active}
                            onChange={() => setPayType(option.value)}
                            className="sr-only"
                          />
                          {option.label}
                        </label>
                      );
                    })}
                  </div>
                </fieldset>

                {error ? (
                  <p className="rounded-md border border-error/30 bg-red-50 px-3 py-2 text-sm font-medium text-error">
                    {error}
                  </p>
                ) : null}

                {status ? (
                  <p className="rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-sm font-bold text-ink">
                    {status}
                  </p>
                ) : null}

                <button
                  type="submit"
                  disabled={isLoadingPlans || isSubmitting || !selectedPlan}
                  className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-black text-white transition-refined hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60 sm:w-fit"
                >
                  {isSubmitting ? (
                    <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                  ) : (
                    <WalletCards aria-hidden="true" className="h-4 w-4" />
                  )}
                  {selectedPlan?.price === "0.00" ? "启用套餐" : "前往支付"}
                </button>
              </form>
            </section>

            <aside className="rounded-lg border border-border bg-surface p-4 shadow-soft">
              <p className="text-sm font-black">订单预览</p>
              <dl className="mt-4 grid gap-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-ink-light">套餐</dt>
                  <dd className="font-bold">{selectedPlan?.name || "未选择"}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-ink-light">金额</dt>
                  <dd className="font-bold">
                    {selectedPlan ? `¥${selectedPlan.price}` : "-"}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-ink-light">每日</dt>
                  <dd className="font-bold">
                    {selectedPlan ? `${selectedPlan.dailyImageLimit} 张` : "-"}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-ink-light">每月</dt>
                  <dd className="font-bold">
                    {selectedPlan ? `${selectedPlan.monthlyImageLimit} 张` : "-"}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-ink-light">渠道</dt>
                  <dd className="font-bold">
                    {payTypes.find((item) => item.value === payType)?.label}
                  </dd>
                </div>
              </dl>
            </aside>
          </div>
    </AppShell>
  );
}
