"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { KeyRound, Loader2, RefreshCcw } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import {
  listUsers,
  resetUserPassword,
  updateUser,
  type CurrentUser,
} from "@/lib/auth-api";

type PasswordInputs = Record<string, string>;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

export default function AdminAccountsPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<CurrentUser[]>([]);
  const [passwords, setPasswords] = useState<PasswordInputs>({});
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [busyUserId, setBusyUserId] = useState("");

  const loadUsers = useCallback(async () => {
    if (!user?.isAdmin) {
      return;
    }

    setIsLoading(true);
    setError("");
    try {
      const envelope = await listUsers();
      setUsers(envelope.users);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "账号列表加载失败。");
    } finally {
      setIsLoading(false);
    }
  }, [user?.isAdmin]);

  useEffect(() => {
    if (!user?.isAdmin) {
      return;
    }

    async function loadInitialUsers() {
      setIsLoading(true);
      setError("");
      try {
        const envelope = await listUsers();
        setUsers(envelope.users);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "账号列表加载失败。");
      } finally {
        setIsLoading(false);
      }
    }

    void loadInitialUsers();
  }, [user?.isAdmin]);

  async function handleToggleActive(target: CurrentUser) {
    if (target.userId === user?.userId) {
      return;
    }

    setBusyUserId(target.userId);
    setError("");
    setStatus("");
    try {
      await updateUser(target.userId, { isActive: !target.isActive });
      setStatus(`${target.username} 已${target.isActive ? "停用" : "启用"}`);
      await loadUsers();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "账号状态更新失败。");
    } finally {
      setBusyUserId("");
    }
  }

  async function handleResetPassword(
    event: FormEvent<HTMLFormElement>,
    target: CurrentUser,
  ) {
    event.preventDefault();
    const password = passwords[target.userId]?.trim() || "";
    if (!password) {
      setError("请输入新密码。");
      return;
    }

    setBusyUserId(target.userId);
    setError("");
    setStatus("");
    try {
      await resetUserPassword(target.userId, password);
      setPasswords((current) => ({ ...current, [target.userId]: "" }));
      setStatus(`${target.username} 的密码已重置`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "密码重置失败。");
    } finally {
      setBusyUserId("");
    }
  }

  if (!user?.isAdmin) {
    return (
      <AppShell fit="center">
        <div className="w-full max-w-sm rounded-lg border border-border bg-surface p-6 text-center shadow-soft">
            <h1 className="text-xl font-black">无权访问</h1>
            <p className="mt-2 text-sm text-ink-light">
              当前账号没有账号管理权限。
            </p>
          </div>
      </AppShell>
    );
  }

  return (
    <AppShell fit="page">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase text-accent">Admin</p>
              <h1 className="mt-1 text-2xl font-black">账号管理</h1>
            </div>
            <button
              type="button"
              onClick={() => void loadUsers()}
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

          <div className="overflow-x-auto rounded-lg border border-border bg-surface shadow-soft">
            <table className="w-full min-w-[760px] border-collapse text-left text-sm">
              <caption className="sr-only">
                账号列表，可查看用户状态、启停账号并重置密码。
              </caption>
              <thead className="bg-surface-soft text-xs uppercase text-ink-light">
                <tr>
                  <th className="px-4 py-3 font-bold">用户</th>
                  <th className="px-4 py-3 font-bold">角色</th>
                  <th className="px-4 py-3 font-bold">状态</th>
                  <th className="px-4 py-3 font-bold">创建日期</th>
                  <th className="px-4 py-3 font-bold">密码</th>
                  <th className="px-4 py-3 font-bold">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((account) => {
                  const isSelf = account.userId === user.userId;
                  const isBusy = busyUserId === account.userId;

                  return (
                    <tr key={account.userId} className="border-t border-border">
                      <td className="max-w-[220px] px-4 py-3">
                        <p className="truncate font-bold text-ink">{account.username}</p>
                        <p className="truncate text-xs text-ink-light">{account.email}</p>
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-md bg-paper-dim px-2 py-1 text-xs font-bold text-ink-light">
                          {account.isAdmin ? "管理员" : "成员"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-md px-2 py-1 text-xs font-bold ${
                            account.isActive
                              ? "bg-accent-soft text-accent"
                              : "bg-paper-dim text-ink-light"
                          }`}
                        >
                          {account.isActive ? "启用" : "停用"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-ink-light">
                        {formatDate(account.createdAt)}
                      </td>
                      <td className="px-4 py-3">
                        <form
                          onSubmit={(event) => void handleResetPassword(event, account)}
                          className="flex min-w-[210px] items-center gap-2"
                        >
                          <input
                            type="password"
                            value={passwords[account.userId] || ""}
                            onChange={(event) =>
                              setPasswords((current) => ({
                                ...current,
                                [account.userId]: event.target.value,
                              }))
                            }
                            placeholder="新密码"
                            className="h-9 w-32 rounded-md border border-border bg-surface px-2 text-sm outline-none transition-refined focus:border-border-hover"
                          />
                          <button
                            type="submit"
                            disabled={isBusy}
                            className="grid h-9 w-9 place-items-center rounded-md border border-border text-ink-light transition-refined hover:border-border-hover hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
                            aria-label={`重置 ${account.username} 密码`}
                          >
                            {isBusy ? (
                              <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" />
                            ) : (
                              <KeyRound aria-hidden="true" className="h-4 w-4" />
                            )}
                          </button>
                        </form>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => void handleToggleActive(account)}
                          disabled={isSelf || isBusy}
                          className="h-9 rounded-md bg-ink px-3 text-xs font-bold text-white transition-refined hover:bg-accent disabled:cursor-not-allowed disabled:bg-paper-dim disabled:text-ink-lighter"
                        >
                          {isSelf ? "当前账号" : account.isActive ? "停用" : "启用"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {!isLoading && users.length === 0 ? (
              <p className="border-t border-border px-4 py-8 text-center text-sm text-ink-light">
                暂无账号。
              </p>
            ) : null}
          </div>
    </AppShell>
  );
}
