import Link from "next/link";
import { ArrowUpRight, PackageSearch, Sparkles, UserRound, Wand2 } from "lucide-react";
import type { ImageTool } from "@/lib/tools";

const iconMap = {
  sparkles: Sparkles,
  wand: Wand2,
  user: UserRound,
  package: PackageSearch,
};

const accentClasses = {
  teal: "border-teal-700/20 bg-teal-50 text-teal-900",
  red: "border-red-700/20 bg-red-50 text-red-900",
  blue: "border-blue-700/20 bg-blue-50 text-blue-900",
  gold: "border-amber-700/25 bg-amber-50 text-amber-950",
};

export function ToolCard({ tool }: { tool: ImageTool }) {
  const Icon = iconMap[tool.icon];

  return (
    <Link
      href={`/tools/${tool.id}`}
      className="group grid min-h-56 content-between rounded-lg border border-zinc-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-zinc-950 hover:shadow-lg"
    >
      <div>
        <div className="flex items-start justify-between gap-3">
          <div
            className={`inline-flex h-11 w-11 items-center justify-center rounded-md border ${accentClasses[tool.accent]}`}
          >
            <Icon aria-hidden="true" className="h-5 w-5" />
          </div>
          <ArrowUpRight
            aria-hidden="true"
            className="h-4 w-4 text-zinc-400 transition group-hover:text-zinc-950"
          />
        </div>
        <p className="mt-5 text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
          {tool.eyebrow}
        </p>
        <h2 className="mt-2 text-2xl font-semibold leading-tight text-zinc-950">
          {tool.title}
        </h2>
        <p className="mt-3 text-sm leading-6 text-zinc-600">{tool.description}</p>
      </div>
      <div className="mt-6 flex flex-wrap gap-2">
        {tool.examples.map((example) => (
          <span
            key={example}
            className="rounded border border-zinc-200 px-2 py-1 text-xs text-zinc-600"
          >
            {example}
          </span>
        ))}
      </div>
    </Link>
  );
}
