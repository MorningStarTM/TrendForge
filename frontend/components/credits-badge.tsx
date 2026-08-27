"use client";

import { useEffect, useState } from "react";

import { fetchCredits } from "@/lib/api";

// ScrapeCreators credit balance, shown in the top corner. Refreshes on mount
// and every 30s (also re-poll after a pull via the `refreshKey` prop).
export function CreditsBadge({ refreshKey }: { refreshKey?: number }) {
  const [credits, setCredits] = useState<number | null | undefined>(undefined);

  useEffect(() => {
    let active = true;
    const load = () => fetchCredits().then((c) => active && setCredits(c)).catch(() => {});
    load();
    const id = setInterval(load, 30_000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [refreshKey]);

  return (
    <div className="flex items-center gap-2 rounded-lg border border-[var(--line)] bg-white px-3 py-1.5 text-sm">
      <span aria-hidden>⚡</span>
      <span className="text-[var(--muted)]">Credits</span>
      <span className="font-bold tabular-nums">
        {credits === undefined ? "…" : credits === null ? "—" : credits.toLocaleString()}
      </span>
    </div>
  );
}
