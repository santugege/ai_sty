import { ToolCard } from "@/components/tool-card";
import { imageTools } from "@/lib/tools";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-8 sm:px-8 lg:px-10">
      <header className="grid gap-6 border-b border-stone-300 pb-8 lg:grid-cols-[1fr_0.75fr] lg:items-end">
        <div>
          <p className="text-sm uppercase tracking-[0.22em] text-stone-500">
            OpenAI image studio
          </p>
          <h1 className="mt-4 max-w-4xl text-5xl font-semibold leading-[1.04] text-stone-950 sm:text-6xl lg:text-7xl">
            图片生成工具箱
          </h1>
        </div>
        <p className="max-w-xl text-lg leading-8 text-stone-600">
          选择一个功能，输入描述或上传图片，由 Python 后端安全调用 OpenAI 图片模型生成结果。
        </p>
      </header>

      <section className="grid flex-1 gap-4 py-8 sm:grid-cols-2 xl:grid-cols-4">
        {imageTools.map((tool) => (
          <ToolCard key={tool.id} tool={tool} />
        ))}
      </section>
    </main>
  );
}
