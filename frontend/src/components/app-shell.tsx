"use client";

import type { ReactNode } from "react";
import { AppNav } from "@/components/app-nav";

type AppShellFit = "workbench" | "page" | "center";

type AppShellProps = {
  children: ReactNode;
  fit?: AppShellFit;
  contentClassName?: string;
  dockClassName?: string;
};

function classNames(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function AppShell({
  children,
  fit = "workbench",
  contentClassName,
  dockClassName,
}: AppShellProps) {
  return (
    <main className="homepageShell min-h-screen bg-paper text-ink">
      <div className="grid min-h-screen xl:grid-cols-[10rem_minmax(0,1fr)]">
        <AppNav />

        <section
          className={classNames(
            "min-w-0 px-4 py-5 sm:px-6 lg:px-8",
            fit === "workbench"
              ? "xl:h-screen xl:min-h-0 xl:overflow-hidden"
              : "min-h-screen",
            contentClassName,
          )}
        >
          <section
            className={classNames(
              "homepageWorkbenchDock min-w-0",
              fit === "workbench" && "xl:h-full xl:min-h-0",
              fit === "page" && "mx-auto w-full max-w-6xl",
              fit === "center" &&
                "grid min-h-[calc(100vh-2.5rem)] w-full place-items-center",
              dockClassName,
            )}
          >
            {children}
          </section>
        </section>
      </div>
    </main>
  );
}
