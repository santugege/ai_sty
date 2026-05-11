import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
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
    title: tool ? `${tool.title} | 图像指挥台` : "图像指挥台",
  };
}

export default async function ToolPage({ params }: ToolPageProps) {
  const { toolId } = await params;
  const tool = getToolById(toolId);

  if (!tool || tool.id !== "product") {
    notFound();
  }

  return (
    <AppShell contentClassName="bg-paper text-ink">
      <ProductWorkbench tool={tool} variant="compact" />
    </AppShell>
  );
}
