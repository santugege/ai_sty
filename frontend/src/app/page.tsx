import { notFound } from "next/navigation";
import { HomeProductWorkbench } from "@/components/home-product-workbench";
import { getToolById } from "@/lib/tools";

export default function Home() {
  const tool = getToolById("product");

  if (!tool) {
    notFound();
  }

  return <HomeProductWorkbench tool={tool} />;
}
