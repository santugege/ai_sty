import Link from "next/link";
import { PackageSearch, Sparkles, UserRound, Wand2 } from "lucide-react";
import type { ImageTool } from "@/lib/tools";

const iconMap = {
  sparkles: Sparkles,
  wand: Wand2,
  user: UserRound,
  package: PackageSearch,
};

const accentClasses = {
  teal: "border-teal-700/25 bg-teal-50 text-teal-900",
  red: "border-red-700/25 bg-red-50 text-red-900",
  blue: "border-blue-700/25 bg-blue-50 text-blue-900",
  gold: "border-amber-700/30 bg-amber-50 text-amber-950",
};

export function ToolCard({ tool }: { tool: ImageTool }) {
  const Icon = iconMap[tool.icon];

  return (
    <Link
      href={`/tools/${tool.id}`}
      className="group grid min-h-64 content-between rounded-lg border border-stone-300 bg-white/75 p-6 shadow-sm transition duration-200 hover:-translate-y-1 hover:border-stone-950 hover:shadow-xl"
    >
      <div>
        <div
          className={`mb-5 inline-flex h-12 w-12 items-center justify-center rounded-md border ${accentClasses[tool.accent]}`}
        >
          <Icon aria-hidden="true" className="h-6 w-6" />
        </div>
        <p className="text-sm uppercase tracking-[0.18em] text-stone-500">
          {tool.eyebrow}
        </p>
        <h2 className="mt-3 text-3xl font-semibold leading-tight text-stone-950">
          {tool.title}
        </h2>
        <p className="mt-4 text-base leading-7 text-stone-600">
          {tool.description}
        </p>
      </div>
      <div className="mt-8 flex flex-wrap gap-2">
        {tool.examples.map((example) => (
          <span
            key={example}
            className="rounded border border-stone-300 px-2.5 py-1 text-sm text-stone-600"
          >
            {example}
          </span>
        ))}
      </div>
    </Link>
  );
}
