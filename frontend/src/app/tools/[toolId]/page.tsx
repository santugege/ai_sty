import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { notFound } from "next/navigation";
import { ProductWorkbench } from "@/components/product-workbench";
import { ToolForm } from "@/components/tool-form";
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
    title: tool ? `${tool.title} | Image Toolbox` : "Image Toolbox",
  };
}

export default async function ToolPage({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  if (!tool) {
    notFound();
  }

  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-5 py-8 sm:px-8 lg:px-10">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm font-semibold text-stone-600 transition hover:text-stone-950"
      >
        <ArrowLeft aria-hidden="true" className="h-4 w-4" />
        返回工具箱
      </Link>

      <header className="mt-8 grid gap-5 border-b border-stone-300 pb-8 lg:grid-cols-[1fr_0.72fr] lg:items-end">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-stone-500">
            {tool.eyebrow}
          </p>
          <h1 className="mt-4 text-5xl font-semibold leading-tight text-stone-950">
            {tool.title}
          </h1>
        </div>
        <p className="max-w-xl text-lg leading-8 text-stone-600">
          {tool.description}
        </p>
      </header>

      <section className="py-8">
        {tool.id === "product" ? (
          <ProductWorkbench tool={tool} />
        ) : (
          <ToolForm tool={tool} />
        )}
      </section>
    </main>
  );
}
