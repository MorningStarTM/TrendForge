"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { TrendCard } from "@/components/trend-card";
import { approveTrend, fetchTrends, rejectTrend } from "@/lib/api";
import type { Trend } from "@/lib/types";

export default function TrendQueuePage() {
  const router = useRouter();
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [tab, setTab] = useState<"pending" | "all">("pending");

  useEffect(() => {
    fetchTrends()
      .then(setTrends)
      .finally(() => setLoading(false));
  }, []);

  async function onApprove(trend: Trend) {
    setBusyId(trend.id);
    try {
      await approveTrend(trend.id);
      router.push(`/trends/${trend.id}`);
    } finally {
      setBusyId(null);
    }
  }

  async function onReject(trend: Trend) {
    setBusyId(trend.id);
    try {
      const updated = await rejectTrend(trend.id);
      setTrends((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } finally {
      setBusyId(null);
    }
  }

  const visible = tab === "pending" ? trends.filter((t) => t.status === "pending") : trends;
  const pendingCount = trends.filter((t) => t.status === "pending").length;

  return (
    <div>
      <header className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">Trends</h1>
          <p className="text-sm text-[var(--muted)]">
            Step 2 — review detected trends and approve the ones worth generating content for.
          </p>
        </div>
        {trends.length > 0 && (
          <div className="flex rounded-lg border border-[var(--line)] bg-white p-1 text-sm">
            {(["pending", "all"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`rounded-md px-3 py-1 font-medium capitalize ${
                  tab === t ? "bg-[var(--brand)] text-[var(--brand-ink)]" : "text-gray-500"
                }`}
              >
                {t}
                {t === "pending" ? ` (${pendingCount})` : ""}
              </button>
            ))}
          </div>
        )}
      </header>

      {loading ? (
        <p className="text-sm text-[var(--muted)]">Loading trends…</p>
      ) : trends.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="mb-4 text-sm text-[var(--muted)]">
            No trends yet — pull posts first to detect them.
          </p>
          <Link href="/" className="btn-primary">
            ← Go to Pull Posts
          </Link>
        </div>
      ) : visible.length === 0 ? (
        <div className="card p-10 text-center text-sm text-[var(--muted)]">
          No {tab} trends right now.
        </div>
      ) : (
        <div className="space-y-4">
          {visible.map((trend) => (
            <TrendCard
              key={trend.id}
              trend={trend}
              onApprove={onApprove}
              onReject={onReject}
              busy={busyId === trend.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
