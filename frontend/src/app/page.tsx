import { notFound } from "next/navigation";
import { AppNav } from "@/components/app-nav";
import { ProductWorkbench } from "@/components/product-workbench";
import { getToolById } from "@/lib/tools";

export default function Home() {
  const tool = getToolById("product");

  if (!tool) {
    notFound();
  }

  return (
    <main className="homepageShell min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen xl:grid-cols-[10rem_minmax(0,1fr)]">
        <AppNav />

        <section className="min-w-0 px-4 py-5 sm:px-6 lg:px-8">
          <section className="homepageWorkbenchDock min-w-0">
            <ProductWorkbench tool={tool} variant="compact" />
          </section>
        </section>
      </div>
    </main>
  );
}
