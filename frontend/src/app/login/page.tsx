"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { Loader2, LogIn } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { loginAccount } from "@/lib/auth-api";
import { safeNextPath } from "@/lib/safe-next-path";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await loginAccount({ email, password });
      await refreshUser();
      router.replace(safeNextPath(searchParams.get("next")));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "登录失败，请稍后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="grid gap-4">
      <label className="grid gap-2 text-sm font-semibold text-ink">
        邮箱
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
          className="h-11 rounded-md border border-border bg-surface px-3 text-sm outline-none transition-refined focus:border-border-hover"
        />
      </label>

      <label className="grid gap-2 text-sm font-semibold text-ink">
        密码
        <input
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
          className="h-11 rounded-md border border-border bg-surface px-3 text-sm outline-none transition-refined focus:border-border-hover"
        />
      </label>

      {error ? (
        <p className="rounded-md border border-error/30 bg-red-50 px-3 py-2 text-sm font-medium text-error">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-ink px-4 text-sm font-bold text-white transition-refined hover:bg-accent disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? (
          <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
        ) : (
          <LogIn aria-hidden="true" className="h-4 w-4" />
        )}
        {isSubmitting ? "正在登录..." : "登录"}
      </button>

      <p className="text-center text-sm text-ink-light">
        还没有账号？{" "}
        <Link href="/register" className="font-semibold text-accent">
          注册
        </Link>
      </p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-paper px-4 py-8 text-ink">
      <section className="w-full max-w-sm rounded-lg border border-border bg-surface p-6 shadow-soft">
        <div className="mb-6">
          <p className="text-xs font-bold uppercase text-accent">Account</p>
          <h1 className="mt-2 text-2xl font-black">登录工作台</h1>
        </div>
        <Suspense fallback={<p className="text-sm text-ink-light">正在准备登录...</p>}>
          <LoginForm />
        </Suspense>
      </section>
    </main>
  );
}
