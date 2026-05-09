import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowLeft, Bolt, Layers3, Sparkles } from "lucide-react";
import { notFound } from "next/navigation";
import { ProductWorkbench } from "@/components/product-workbench";
import { getToolById, imageTools } from "@/lib/tools";

type ToolPageProps = {
  params: Promise<{
    toolId: string;
  }>;
};

export function generateStaticParams() {
  return imageTools.map((tool) => ({
    toolId: tool.id,
  }));
}

export async function generateMetadata({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  return {
    title: tool ? `${tool.title} | Studio Matrix` : "Studio Matrix",
  };
}

export default async function ToolPage({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  if (!tool || tool.id !== "product") {
    notFound();
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-paper text-ink">
      <div className="relative z-10 px-4 py-4 sm:px-6 lg:px-8">
        <div className="toolTopBar mx-auto flex min-w-0 max-w-[1800px] flex-col gap-4 overflow-hidden rounded-[1.35rem] border border-border bg-surface/80 px-4 py-3 shadow-soft backdrop-blur lg:flex-row lg:items-center lg:justify-between">
          <div className="flex min-w-0 items-center gap-4">
            <Link
              href="/"
              className="group grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-border bg-paper-subtle text-ink-lighter transition-colors hover:border-cyan hover:text-cyan"
              aria-label="Studio Matrix"
            >
              <ArrowLeft
                aria-hidden="true"
                className="h-4 w-4 transition-transform group-hover:-translate-x-1"
              />
            </Link>

            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-cyan/30 bg-cyan/10 text-cyan">
              <Sparkles aria-hidden="true" className="h-5 w-5" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-3">
                <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.32em] text-cyan">
                  Studio Matrix
                </p>
                <span className="hidden h-1.5 w-1.5 rounded-full bg-cyan shadow-[0_0_14px_rgba(73,245,212,0.9)] sm:block" />
              </div>
              <h1 className="mt-1 truncate font-serif text-2xl font-light leading-tight text-ink">
                {tool.title}
              </h1>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:w-[34rem]">
            <StatusPill icon={<Bolt aria-hidden="true" className="h-4 w-4" />} label="实时创作" />
            <StatusPill icon={<Layers3 aria-hidden="true" className="h-4 w-4" />} label="多风格输出" />
            <p className="min-w-0 border-l border-border pl-4 text-xs leading-5 text-ink-light [overflow-wrap:anywhere] sm:col-span-2">
              {tool.description}
            </p>
          </div>
        </div>
      </div>

      <section className="relative z-10">
        <ProductWorkbench tool={tool} />
      </section>
    </main>
  );
}

function StatusPill({
  icon,
  label,
}: {
  icon: ReactNode;
  label: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm text-ink-light">
      <span className="text-cyan">{icon}</span>
      {label}
    </div>
  );
}
