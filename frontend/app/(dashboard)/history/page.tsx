"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { fetchHistory } from "@/lib/api";
import type { HistoryEntry } from "@/lib/types";

const ACTION_TONE: Record<string, "green" | "red" | "amber" | "blue" | "neutral"> = {
  approved: "green",
  rejected: "red",
  refined: "amber",
  pulled: "blue",
};

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHistory()
      .then(setEntries)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold">History</h1>
        <p className="text-sm text-[var(--muted)]">Every approval, rejection, and refinement.</p>
      </header>

      {loading ? (
        <p className="text-sm text-[var(--muted)]">Loading…</p>
      ) : entries.length === 0 ? (
        <div className="card p-10 text-center text-sm text-[var(--muted)]">
          No activity yet. Approve or reject a trend to see it here.
        </div>
      ) : (
        <div className="card divide-y divide-[var(--line)]">
          {entries.map((e) => (
            <div key={e.id} className="flex items-start justify-between gap-4 px-5 py-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Badge tone={ACTION_TONE[e.action] ?? "neutral"}>{e.action}</Badge>
                  <span className="text-sm font-medium">{e.label}</span>
                </div>
                {e.notes && <p className="mt-1 text-xs text-[var(--muted)]">“{e.notes}”</p>}
              </div>
              <time className="shrink-0 text-xs text-[var(--muted)]">
                {new Date(e.at).toLocaleString()}
              </time>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
