"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { TrendCard } from "@/components/trend-card";
import { Button } from "@/components/ui/button";
import { fetchTrends } from "@/lib/api";
import type { Trend } from "@/lib/types";

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[] | null>(null);

  useEffect(() => {
    fetchTrends()
      .then(setTrends)
      .catch(() => setTrends([]));
  }, []);

  if (trends === null) {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton h-28 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (trends.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center px-6 py-16 text-center">
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--panel-2)] text-[var(--faint)]">
          <Icon.Trends className="h-7 w-7" />
        </div>
        <h3 className="text-base font-semibold">No trends yet</h3>
        <p className="mt-1 max-w-sm text-sm text-[var(--muted)]">
          Run a discovery to detect trends from live posts.
        </p>
        <Link href="/" className="mt-5">
          <Button>
            <Icon.Discover className="h-4 w-4" /> Go to Discover
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div>
      <p className="mb-4 text-sm text-[var(--muted)]">
        {trends.length} trend{trends.length === 1 ? "" : "s"} detected · ranked by strength
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {trends.map((t) => (
          <TrendCard key={t.id} trend={t} />
        ))}
      </div>
    </div>
  );
}
