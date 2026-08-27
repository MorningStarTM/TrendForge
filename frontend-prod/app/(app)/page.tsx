"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Icon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { fetchLastRun, startDiscovery } from "@/lib/api";
import type { IngestionRun } from "@/lib/types";

const WINDOWS = [
  { label: "Last 24 hours", value: 24 },
  { label: "Last 3 days", value: 72 },
  { label: "Last 7 days", value: 168 },
  { label: "Last 30 days", value: 720 },
  { label: "All time", value: 0 },
];

export default function DiscoverPage() {
  const [query, setQuery] = useState("");
  const [targetPosts, setTargetPosts] = useState(40);
  const [windowHours, setWindowHours] = useState(72);
  const [staticOnly, setStaticOnly] = useState(false);

  const [run, setRun] = useState<IngestionRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLastRun().then(setRun).catch(() => {});
  }, []);

  async function onDiscover(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) {
      setError("Enter a topic to discover trends for.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await startDiscovery({
        query: query.trim(),
        target_posts: targetPosts,
        window_hours: windowHours,
        static_only: staticOnly,
      });
      setRun(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Discovery failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
      {/* Parameters */}
      <form onSubmit={onDiscover} className="card h-fit p-6">
        <div className="mb-5 flex items-center gap-2">
          <Icon.Discover className="h-5 w-5 text-[var(--ink)]" />
          <h2 className="text-base font-bold">New discovery</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label" htmlFor="query">
              Topic
            </label>
            <input
              id="query"
              className="input"
              placeholder="e.g. pizza, cheese pull, ramadan"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <p className="mt-1.5 text-xs text-[var(--muted)]">
              What to search for across public posts.
            </p>
          </div>

          <div>
            <label className="label" htmlFor="count">
              Posts to pull
            </label>
            <input
              id="count"
              type="number"
              min={10}
              max={2000}
              step={10}
              className="input"
              value={targetPosts}
              onChange={(e) => setTargetPosts(Number(e.target.value))}
            />
            <p className="mt-1.5 text-xs text-[var(--muted)]">
              More posts surface more trends but spend more credits.
            </p>
          </div>

          <div>
            <label className="label" htmlFor="window">
              Detection window
            </label>
            <select
              id="window"
              className="input"
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
            >
              {WINDOWS.map((w) => (
                <option key={w.value} value={w.value}>
                  {w.label}
                </option>
              ))}
            </select>
            <p className="mt-1.5 text-xs text-[var(--muted)]">
              Only posts within this window are clustered into trends.
            </p>
          </div>

          <label className="flex cursor-pointer items-center justify-between rounded-xl border border-[var(--line)] bg-[var(--panel-2)] px-3.5 py-3">
            <span className="text-sm">
              <span className="font-medium">Static posts only</span>
              <span className="block text-xs text-[var(--muted)]">Photos only — no video</span>
            </span>
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--dark)]"
              checked={staticOnly}
              onChange={(e) => setStaticOnly(e.target.checked)}
            />
          </label>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}

          <Button type="submit" disabled={busy} className="w-full">
            {busy ? (
              <>
                <Spinner /> Discovering…
              </>
            ) : (
              <>
                <Icon.Sparkles className="h-4 w-4" /> Discover trends
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Results */}
      <div className="space-y-6">
        {busy && (
          <div className="card flex items-center gap-3 p-6 text-sm text-gray-600">
            <Spinner />
            Pulling posts and detecting trends — this can take a moment.
          </div>
        )}

        {!busy && !run && (
          <div className="card flex flex-col items-center justify-center px-6 py-16 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--panel-2)] text-[var(--faint)]">
              <Icon.Discover className="h-7 w-7" />
            </div>
            <h3 className="text-base font-semibold">Discover your first trends</h3>
            <p className="mt-1 max-w-sm text-sm text-[var(--muted)]">
              Enter a topic and run a discovery. Detected trends will appear here and on the
              Trends page.
            </p>
          </div>
        )}

        {!busy && run && <RunSummary run={run} />}
      </div>
    </div>
  );
}

function RunSummary({ run }: { run: IngestionRun }) {
  const funnel = [
    { label: "Pulled", value: run.total_posts },
    { label: "In pool", value: run.pool_posts ?? run.total_posts },
    { label: "In window", value: run.posts_in_window ?? 0 },
    { label: "Candidates", value: run.candidates_built ?? 0 },
    { label: "Trends", value: run.trends_detected, highlight: true },
  ];

  return (
    <div className="animate-fade-in space-y-6">
      <div className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <span className="eyebrow">Latest discovery</span>
            <h2 className="text-xl font-bold">“{run.query}”</h2>
          </div>
          <Link href="/trends">
            <Button variant="dark">
              View {run.trends_detected} trend{run.trends_detected === 1 ? "" : "s"}
              <Icon.Arrow className="h-4 w-4" />
            </Button>
          </Link>
        </div>

        {/* Funnel */}
        <div className="mt-5 grid grid-cols-5 gap-2">
          {funnel.map((f, i) => (
            <div key={f.label} className="relative">
              <div
                className={`rounded-xl border p-3 text-center ${
                  f.highlight
                    ? "border-[var(--brand-deep)] bg-[#fcfcdf]"
                    : "border-[var(--line)] bg-[var(--panel-2)]"
                }`}
              >
                <div className="text-2xl font-extrabold tabular-nums">{f.value}</div>
                <div className="mt-0.5 text-[11px] font-medium text-[var(--muted)]">
                  {f.label}
                </div>
              </div>
              {i < funnel.length - 1 && (
                <Icon.Arrow className="absolute -right-[9px] top-1/2 z-10 hidden h-3.5 w-3.5 -translate-y-1/2 text-[var(--faint)] sm:block" />
              )}
            </div>
          ))}
        </div>

        {run.trends_detected === 0 && (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            No trends in this window. Try widening the detection window or pulling more posts —
            search results are often older than 24 hours.
          </div>
        )}
      </div>
    </div>
  );
}
