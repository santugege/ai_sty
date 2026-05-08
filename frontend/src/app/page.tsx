import type { ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BadgePercent,
  ImagePlus,
  Layers3,
  PackageSearch,
  Sparkles,
} from "lucide-react";
import { ToolCard } from "@/components/tool-card";
import {
  imageTools,
  productImagePurposes,
  productPlatformStyles,
} from "@/lib/tools";

export default function Home() {
  const productTool = imageTools.find((tool) => tool.id === "product");
  const supportingTools = imageTools.filter((tool) => tool.id !== "product");

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col gap-5 border-b border-zinc-300 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-zinc-600">
            <PackageSearch aria-hidden="true" className="h-3.5 w-3.5" />
            Ecommerce image studio
          </p>
          <h1 className="mt-4 max-w-4xl text-4xl font-semibold leading-tight text-zinc-950 sm:text-5xl lg:text-6xl">
            电商商品图工作台
          </h1>
        </div>
        <p className="max-w-xl text-base leading-7 text-zinc-600">
          从商品原图出发，按拼多多、淘宝天猫、京东、小红书、抖音电商等实际平台流程生成主图、白底图、场景图和促销图。
        </p>
      </header>

      {productTool && (
        <>
          <section className="grid gap-5 py-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)]">
            <Link
              href="/tools/product"
              className="group overflow-hidden rounded-lg border border-zinc-950 bg-zinc-950 text-white shadow-xl transition hover:-translate-y-0.5"
            >
              <div className="grid min-h-[25rem] gap-6 p-6 sm:p-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(18rem,0.65fr)]">
                <div className="flex flex-col justify-between gap-8">
                  <div>
                    <div className="inline-flex h-12 w-12 items-center justify-center rounded-md bg-white text-zinc-950">
                      <ImagePlus aria-hidden="true" className="h-6 w-6" />
                    </div>
                    <p className="mt-6 text-sm font-semibold uppercase tracking-[0.16em] text-zinc-400">
                      {productTool.eyebrow}
                    </p>
                    <h2 className="mt-3 max-w-2xl text-4xl font-semibold leading-tight sm:text-5xl">
                      按真实平台流程生成商品图
                    </h2>
                    <p className="mt-4 max-w-2xl text-base leading-7 text-zinc-300">
                      不再只写一句提示词。先选平台和用途，再补卖点、场景、促销和保真要求，让模型按运营目标工作。
                    </p>
                  </div>
                  <span className="inline-flex w-fit items-center gap-2 rounded-md bg-white px-4 py-2.5 text-sm font-semibold text-zinc-950 transition group-hover:bg-amber-200">
                    打开商品图工作台
                    <ArrowRight aria-hidden="true" className="h-4 w-4" />
                  </span>
                </div>

                <div className="grid content-start gap-3">
                  <PreviewPanel
                    icon={
                      <BadgePercent aria-hidden="true" className="h-4 w-4" />
                    }
                    title="平台风格"
                    items={productPlatformStyles.map((item) => item.label)}
                  />
                  <PreviewPanel
                    icon={<Layers3 aria-hidden="true" className="h-4 w-4" />}
                    title="图片用途"
                    items={productImagePurposes.map((item) => item.label)}
                  />
                  <div className="rounded-lg border border-white/15 bg-white/10 p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-white">
                      <Sparkles aria-hidden="true" className="h-4 w-4" />
                      一次提交完整运营需求
                    </div>
                    <p className="mt-3 text-sm leading-6 text-zinc-300">
                      商品类目、核心卖点、促销文案、必须保留和禁止元素都会进入后端结构化 prompt。
                    </p>
                  </div>
                </div>
              </div>
            </Link>

            <aside className="grid gap-4">
              {supportingTools.map((tool) => (
                <ToolCard key={tool.id} tool={tool} />
              ))}
            </aside>
          </section>

          <div className="-mt-1 mb-6 rounded-lg border border-zinc-200 bg-white px-4 py-3 shadow-sm">
            <a href="/agent">多轮图片 Agent</a>
          </div>
        </>
      )}
    </main>
  );
}

function PreviewPanel({
  icon,
  title,
  items,
}: {
  icon: ReactNode;
  title: string;
  items: string[];
}) {
  return (
    <div className="rounded-lg border border-white/15 bg-white/10 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-white">
        {icon}
        {title}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className="rounded border border-white/15 bg-white/10 px-2 py-1 text-xs text-zinc-200"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
