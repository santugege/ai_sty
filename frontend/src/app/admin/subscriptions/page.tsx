"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { CheckCircle2, Loader2, Plus, RefreshCcw, XCircle } from "lucide-react";
import { AppNav } from "@/components/app-nav";
import { useAuth } from "@/components/auth-provider";
import {
  createAdminSubscriptionPlan,
  listAdminSubscriptionPlans,
  type PlanInput,
  type SubscriptionPlan,
} from "@/lib/subscription-api";

const initialForm: PlanInput = {
  code: "",
  name: "",
  description: "",
  price: "",
  dailyImageLimit: 0,
  monthlyImageLimit: 0,
  isActive: true,
  isDefault: false,
  sortOrder: 0,
};

function formatPrice(value: string) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return value;
  }
  return `¥${numericValue.toFixed(2)}`;
}

export default function AdminSubscriptionsPage() {
  const { user } = useAuth();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [form, setForm] = useState<PlanInput>(initialForm);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadPlans = useCallback(async () => {
    if (!user?.isAdmin) {
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      const envelope = await listAdminSubscriptionPlans();
      setPlans(envelope.plans);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "套餐列表加载失败。");
    } finally {
      setIsLoading(false);
    }
  }, [user?.isAdmin]);

  useEffect(() => {
    if (!user?.isAdmin) {
      return;
    }

    async function loadInitialPlans() {
      setIsLoading(true);
      setError("");
      try {
        const envelope = await listAdminSubscriptionPlans();
        setPlans(envelope.plans);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "套餐列表加载失败。");
      } finally {
        setIsLoading(false);
      }
    }

    void loadInitialPlans();
  }, [user?.isAdmin]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setIsSubmitting(true);
    setError("");
    setStatus("");
    try {
      await createAdminSubscriptionPlan({
        ...form,
        code: form.code?.trim() || undefined,
        name: form.name.trim(),
        description: form.description.trim(),
        price: form.price.trim(),
        dailyImageLimit: Number(form.dailyImageLimit),
        monthlyImageLimit: Number(form.monthlyImageLimit),
        sortOrder: Number(form.sortOrder),
      });
      setForm(initialForm);
      setStatus("订阅套餐已创建。");
      await loadPlans();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "订阅套餐创建失败。");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!user?.isAdmin) {
    return (
      <main className="grid min-h-screen xl:grid-cols-[10rem_minmax(0,1fr)]">
        <AppNav />
        <section className="grid min-h-screen place-items-center px-4 py-8">
          <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-6 text-center shadow-soft">
            <h1 className="text-xl font-black">无权访问</h1>
            <p className="mt-2 text-sm text-ink-light">
              当前账号没有订阅管理权限。
            </p>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen xl:grid-cols-[10rem_minmax(0,1fr)]">
        <AppNav />

        <section className="min-w-0 px-4 py-5 sm:px-6 lg:px-8">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase text-accent">Admin</p>
              <h1 className="mt-1 text-2xl font-black">订阅管理</h1>
            </div>
            <button
              type="button"
              onClick={() => void loadPlans()}
              disabled={isLoading}
              className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-surface px-3 text-sm font-bold text-ink transition-refined hover:border-border-hover disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? (
                <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCcw aria-hidden="true" className="h-4 w-4" />
              )}
              刷新
            </button>
          </div>

          {error ? (
            <p className="mb-3 rounded-md border border-error/30 bg-red-50 px-3 py-2 text-sm font-medium text-error">
              {error}
            </p>
          ) : null}
          {status ? (
            <p className="mb-3 rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-sm font-medium text-accent">
              {status}
            </p>
          ) : null}

          <form
            onSubmit={(event) => void handleSubmit(event)}
            className="mb-5 rounded-lg border border-border bg-surface p-4 shadow-soft"
          >
            <div className="mb-3 flex items-center gap-2">
              <Plus aria-hidden="true" className="h-4 w-4 text-accent" />
              <h2 className="text-base font-black">新增套餐</h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <label className="grid gap-1 text-xs font-bold text-ink-light">
                编码
                <input
                  value={form.code}
                  onChange={(event) => setForm({ ...form, code: event.target.value })}
                  className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-semibold text-ink outline-none transition-refined focus:border-border-hover"
                  placeholder="pro"
                />
              </label>
              <label className="grid gap-1 text-xs font-bold text-ink-light">
                名称
                <input
                  required
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                  className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-semibold text-ink outline-none transition-refined focus:border-border-hover"
                  placeholder="专业版"
                />
              </label>
              <label className="grid gap-1 text-xs font-bold text-ink-light">
                价格
                <input
                  required
                  inputMode="decimal"
                  value={form.price}
                  onChange={(event) => setForm({ ...form, price: event.target.value })}
                  className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-semibold text-ink outline-none transition-refined focus:border-border-hover"
                  placeholder="29.90"
                />
              </label>
              <label className="grid gap-1 text-xs font-bold text-ink-light">
                排序
                <input
                  type="number"
                  value={form.sortOrder}
                  onChange={(event) =>
                    setForm({ ...form, sortOrder: Number(event.target.value) })
                  }
                  className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-semibold text-ink outline-none transition-refined focus:border-border-hover"
                />
              </label>
              <label className="grid gap-1 text-xs font-bold text-ink-light">
                每日额度
                <input
                  required
                  type="number"
                  min="0"
                  value={form.dailyImageLimit}
                  onChange={(event) =>
                    setForm({ ...form, dailyImageLimit: Number(event.target.value) })
                  }
                  className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-semibold text-ink outline-none transition-refined focus:border-border-hover"
                />
              </label>
              <label className="grid gap-1 text-xs font-bold text-ink-light">
                每月额度
                <input
                  required
                  type="number"
                  min="0"
                  value={form.monthlyImageLimit}
                  onChange={(event) =>
                    setForm({ ...form, monthlyImageLimit: Number(event.target.value) })
                  }
                  className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-semibold text-ink outline-none transition-refined focus:border-border-hover"
                />
              </label>
              <label className="grid gap-1 text-xs font-bold text-ink-light md:col-span-2">
                描述
                <input
                  value={form.description}
                  onChange={(event) =>
                    setForm({ ...form, description: event.target.value })
                  }
                  className="h-10 rounded-md border border-border bg-surface px-3 text-sm font-semibold text-ink outline-none transition-refined focus:border-border-hover"
                  placeholder="适合稳定出图的团队"
                />
              </label>
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
              <div className="flex flex-wrap gap-3">
                <label className="inline-flex items-center gap-2 text-sm font-bold text-ink-light">
                  <input
                    type="checkbox"
                    checked={form.isActive}
                    onChange={(event) =>
                      setForm({ ...form, isActive: event.target.checked })
                    }
                    className="h-4 w-4 rounded border-border"
                  />
                  启用
                </label>
                <label className="inline-flex items-center gap-2 text-sm font-bold text-ink-light">
                  <input
                    type="checkbox"
                    checked={form.isDefault}
                    onChange={(event) =>
                      setForm({ ...form, isDefault: event.target.checked })
                    }
                    className="h-4 w-4 rounded border-border"
                  />
                  默认套餐
                </label>
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex h-10 items-center gap-2 rounded-md bg-ink px-4 text-sm font-bold text-white transition-refined hover:bg-accent disabled:cursor-not-allowed disabled:bg-paper-dim disabled:text-ink-lighter"
              >
                {isSubmitting ? (
                  <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus aria-hidden="true" className="h-4 w-4" />
                )}
                创建套餐
              </button>
            </div>
          </form>

          <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-soft">
            <table className="w-full min-w-[760px] border-collapse text-left text-sm">
              <caption className="sr-only">
                订阅套餐列表，可查看价格、每日额度、每月额度和状态。
              </caption>
              <thead className="bg-surface-soft text-xs uppercase text-ink-light">
                <tr>
                  <th className="px-4 py-3 font-bold">套餐</th>
                  <th className="px-4 py-3 font-bold">价格</th>
                  <th className="px-4 py-3 font-bold">每日额度</th>
                  <th className="px-4 py-3 font-bold">每月额度</th>
                  <th className="px-4 py-3 font-bold">状态</th>
                  <th className="px-4 py-3 font-bold">排序</th>
                </tr>
              </thead>
              <tbody>
                {plans.map((plan) => (
                  <tr key={plan.id} className="border-t border-border">
                    <td className="max-w-[240px] px-4 py-3">
                      <p className="truncate font-bold text-ink">{plan.name}</p>
                      <p className="truncate text-xs text-ink-light">{plan.code}</p>
                    </td>
                    <td className="px-4 py-3 font-bold text-ink">
                      {formatPrice(plan.price)}
                    </td>
                    <td className="px-4 py-3 text-ink-light">
                      {plan.dailyImageLimit}
                    </td>
                    <td className="px-4 py-3 text-ink-light">
                      {plan.monthlyImageLimit}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <span
                          className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-bold ${
                            plan.isActive
                              ? "bg-accent-soft text-accent"
                              : "bg-paper-dim text-ink-light"
                          }`}
                        >
                          {plan.isActive ? (
                            <CheckCircle2 aria-hidden="true" className="h-3 w-3" />
                          ) : (
                            <XCircle aria-hidden="true" className="h-3 w-3" />
                          )}
                          {plan.isActive ? "启用" : "停用"}
                        </span>
                        {plan.isDefault ? (
                          <span className="rounded-md bg-paper-dim px-2 py-1 text-xs font-bold text-ink-light">
                            默认
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-ink-light">{plan.sortOrder}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {!isLoading && plans.length === 0 ? (
              <p className="border-t border-border px-4 py-8 text-center text-sm text-ink-light">
                暂无订阅套餐。
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
