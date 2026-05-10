"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LogOut,
  MessageSquareText,
  Package,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";

const baseItems = [
  { label: "商品图", href: "/", icon: Package },
  { label: "ChatGPT 对话", href: "/agent", icon: MessageSquareText },
];

function isActivePath(pathname: string | null, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname?.startsWith(`${href}/`);
}

export function AppNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const items = user?.isAdmin
    ? [...baseItems, { label: "账号管理", href: "/admin/accounts", icon: ShieldCheck }]
    : baseItems;

  return (
    <>
      <header className="mobileNav border-b border-border bg-surface px-4 py-3 xl:hidden">
        <div className="flex items-center justify-between gap-3">
          <Link href="/" className="min-w-0">
            <span className="block truncate text-base font-black">图像指挥台</span>
            <span className="block truncate text-xs font-medium text-ink-light">
              {user?.username || user?.email}
            </span>
          </Link>
          <button
            type="button"
            onClick={() => void logout()}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border text-ink-light transition-refined hover:border-border-hover hover:text-ink"
            aria-label="退出登录"
          >
            <LogOut aria-hidden="true" className="h-4 w-4" />
          </button>
        </div>

        <nav className="mt-3 flex gap-2 overflow-x-auto" aria-label="移动导航">
          {items.map((item) => {
            const Icon = item.icon;
            const active = isActivePath(pathname, item.href);

            return (
              <Link
                key={item.label}
                href={item.href}
                className={`inline-flex h-10 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-semibold transition-refined ${
                  active
                    ? "bg-ink text-white"
                    : "bg-paper-dim text-ink-light hover:text-ink"
                }`}
              >
                <Icon aria-hidden="true" className="h-3.5 w-3.5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </header>

      <aside className="homepageRail hidden border-r border-border bg-surface px-5 py-7 xl:flex xl:flex-col">
        <Link href="/" className="block">
          <span className="block text-[21px] font-black leading-6 tracking-tight">
            图像指挥台
          </span>
          <span className="mt-2 block text-xs font-medium text-ink-light">
            电商商品图生成
          </span>
        </Link>

        <nav className="mt-8 grid gap-2" aria-label="主导航">
          {items.map((item) => {
            const Icon = item.icon;
            const active = isActivePath(pathname, item.href);

            return (
              <Link
                key={item.label}
                href={item.href}
                className={`flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-refined ${
                  active
                    ? "bg-ink text-white"
                    : "text-ink-light hover:bg-surface-soft hover:text-ink"
                }`}
              >
                <span
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded-md ${
                    active ? "bg-coral text-white" : "bg-paper-dim text-ink-light"
                  }`}
                >
                  <Icon aria-hidden="true" className="h-3.5 w-3.5" />
                </span>
                <span className="min-w-0 truncate">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-border pt-4">
          <div className="mb-3 min-w-0 text-xs text-ink-light">
            <p className="truncate font-semibold text-ink">{user?.username}</p>
            <p className="truncate">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={() => void logout()}
            className="flex min-h-10 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm font-semibold text-ink-light transition-refined hover:bg-surface-soft hover:text-ink"
          >
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-paper-dim text-ink-light">
              <LogOut aria-hidden="true" className="h-3.5 w-3.5" />
            </span>
            <span>退出登录</span>
          </button>
        </div>
      </aside>
    </>
  );
}
