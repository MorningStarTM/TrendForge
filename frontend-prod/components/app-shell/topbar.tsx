"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { fetchCredits } from "@/lib/api";

const TITLES: Record<string, { title: string; sub: string }> = {
  "/": { title: "Discover", sub: "Pull live posts and detect emerging trends" },
  "/trends": { title: "Trends", sub: "Review detected trends and generate content" },
  "/brand": { title: "Brand Knowledge Base", sub: "Guidelines that shape every generation" },
  "/settings": { title: "Settings", sub: "Account and system configuration" },
};

export function Topbar() {
  const pathname = usePathname();
  const [credits, setCredits] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => fetchCredits().then((c) => alive && setCredits(c)).catch(() => {});
    load();
    const t = setInterval(load, 30_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  const meta =
    TITLES[pathname] ??
    (pathname.startsWith("/trends")
      ? { title: "Trend detail", sub: "Review posts and generate content" }
      : { title: "TrendForge", sub: "" });

  return (
    <header className="flex items-center justify-between border-b border-[var(--line)] bg-white/80 px-8 py-4 backdrop-blur">
      <div>
        <h1 className="text-lg font-bold tracking-tight text-[var(--ink)]">{meta.title}</h1>
        {meta.sub && <p className="text-[13px] text-[var(--muted)]">{meta.sub}</p>}
      </div>
      <div
        className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--panel-2)] px-3.5 py-1.5"
        title="ScrapeCreators credit balance"
      >
        <Icon.Bolt className="h-4 w-4 text-[#caab00]" />
        <span className="text-sm font-semibold tabular-nums text-[var(--ink)]">
          {credits === null ? "—" : credits.toLocaleString()}
        </span>
        <span className="text-xs text-[var(--muted)]">credits</span>
      </div>
    </header>
  );
}
