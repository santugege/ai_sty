import { notFound } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ProductWorkbench } from "@/components/product-workbench";
import { getToolById } from "@/lib/tools";

export default function Home() {
  const tool = getToolById("product");

  if (!tool) {
    notFound();
  }

  return (
    <AppShell>
      <ProductWorkbench tool={tool} variant="compact" />
    </AppShell>
  );
}
