import Link from "next/link";
import { notFound } from "next/navigation";
import {
  Layers3,
  MessageSquareText,
  Package,
  Settings2,
} from "lucide-react";
import { ProductWorkbench } from "@/components/product-workbench";
import { getToolById } from "@/lib/tools";

const navItems = [
  { label: "商品图", href: "/", icon: Package, active: true },
  { label: "多轮编辑", href: "/agent", icon: MessageSquareText },
  { label: "素材库", href: "/", icon: Layers3 },
  { label: "设置", href: "/", icon: Settings2 },
];

export default function Home() {
  const tool = getToolById("product");

  if (!tool) {
    notFound();
  }

  return (
    <main className="homepageShell min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen xl:grid-cols-[10rem_minmax(0,1fr)]">
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
            {navItems.map((item) => {
              const Icon = item.icon;

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={`flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold transition-refined ${
                    item.active
                      ? "bg-ink text-white"
                      : "text-ink-light hover:bg-surface-soft hover:text-ink"
                  }`}
                >
                  <span
                    className={`grid h-6 w-6 place-items-center rounded-md ${
                      item.active
                        ? "bg-coral text-white"
                        : "bg-paper-dim text-ink-light"
                    }`}
                  >
                    <Icon aria-hidden="true" className="h-3.5 w-3.5" />
                  </span>
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <section className="min-w-0 px-4 py-5 sm:px-6 lg:px-8">
          <section className="homepageWorkbenchDock min-w-0">
            <ProductWorkbench tool={tool} variant="compact" />
          </section>
        </section>
      </div>
    </main>
  );
}
