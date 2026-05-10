"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Loader2, UserPlus } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { registerAccount } from "@/lib/auth-api";

export default function RegisterPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await registerAccount({ username, email, password });
      await refreshUser();
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "注册失败，请稍后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-paper px-4 py-8 text-ink">
      <section className="w-full max-w-sm rounded-lg border border-border bg-surface p-6 shadow-soft">
        <div className="mb-6">
          <p className="text-xs font-bold uppercase text-accent">Account</p>
          <h1 className="mt-2 text-2xl font-black">创建账号</h1>
          <p className="mt-2 text-sm leading-6 text-ink-light">
            首个注册账号会自动成为管理员。
          </p>
        </div>

        <form onSubmit={handleSubmit} className="grid gap-4">
          <label className="grid gap-2 text-sm font-semibold text-ink">
            用户名
            <input
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
              className="h-11 rounded-md border border-border bg-surface px-3 text-sm outline-none transition-refined focus:border-border-hover"
            />
          </label>

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
              autoComplete="new-password"
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
              <UserPlus aria-hidden="true" className="h-4 w-4" />
            )}
            {isSubmitting ? "正在注册..." : "注册"}
          </button>

          <p className="text-center text-sm text-ink-light">
            已有账号？{" "}
            <Link href="/login" className="font-semibold text-accent">
              登录
            </Link>
          </p>
        </form>
      </section>
    </main>
  );
}
