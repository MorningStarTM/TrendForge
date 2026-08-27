"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchIngestion, startIngestion } from "@/lib/api";
import type { IngestionRun, Platform } from "@/lib/types";

const PLATFORMS: { id: Platform; label: string }[] = [
  { id: "instagram", label: "Instagram" },
  { id: "tiktok", label: "TikTok" },
  { id: "youtube", label: "YouTube" },
];

const WINDOWS: { hours: number; label: string }[] = [
  { hours: 24, label: "Last 24 hours" },
  { hours: 72, label: "Last 3 days" },
  { hours: 168, label: "Last 7 days" },
  { hours: 720, label: "Last 30 days" },
  { hours: 2160, label: "Last 90 days" },
  { hours: 0, label: "All time" },
];

function windowLabel(hours?: number): string {
  if (hours == null) return "window";
  if (hours <= 0) return "all-time";
  return `${hours}h`;
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export default function PullPostsPage() {
  const [query, setQuery] = useState("pizza");
  const [selected, setSelected] = useState<Platform[]>(["instagram", "tiktok", "youtube"]);
  const [staticOnly, setStaticOnly] = useState(false);
  const [targetPosts, setTargetPosts] = useState(30);
  const [windowHours, setWindowHours] = useState(24);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState<string | null>(null);
  const [run, setRun] = useState<IngestionRun | null>(null);

  useEffect(() => {
    fetchIngestion().then(setRun);
  }, []);

  function toggle(p: Platform) {
    setSelected((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  }

  async function onPull() {
    setRunning(true);
    setRun(null);
    const stages = [
      ...selected.map((p) => `Scraping ${p}…`),
      "Normalizing posts…",
      "Scoring velocity…",
      "Detecting trends…",
    ];
    for (const s of stages) {
      setStage(s);
      await sleep(400);
    }
    const result = await startIngestion({
      platforms: selected,
      query,
      static_only: staticOnly,
      target_posts: targetPosts,
      window_hours: windowHours,
    });
    setStage(null);
    setRunning(false);
    setRun(result);
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Pull Posts</h1>
        <p className="text-sm text-[var(--muted)]">
          Step 1 — scrape social posts, normalize them, and detect trends.
        </p>
      </header>

      <div className="card p-6">
        <div className="mb-5 flex flex-wrap gap-6">
          <div>
            <label className="mb-1 block text-sm font-medium">Keyword / hashtag</label>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={running}
              className="input w-64"
              placeholder="e.g. pizza"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Posts to pull (target)</label>
            <input
              type="number"
              min={10}
              max={10000}
              step={10}
              value={targetPosts}
              onChange={(e) => setTargetPosts(Math.max(10, Number(e.target.value) || 10))}
              disabled={running}
              className="input w-40"
            />
            <p className="mt-1 text-xs text-[var(--muted)]">
              ~1 credit per ~10–30 posts. Higher = more static posts, more credits.
            </p>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Detection window</label>
            <select
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              disabled={running}
              className="input w-44"
            >
              {WINDOWS.map((w) => (
                <option key={w.hours} value={w.hours}>
                  {w.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-[var(--muted)]">
              Only posts within this age become trends. Widen it if you get 0.
            </p>
          </div>
        </div>

        <label className="mb-2 block text-sm font-medium">Platforms</label>
        <div className="mb-6 flex flex-wrap gap-2">
          {PLATFORMS.map((p) => {
            const on = selected.includes(p.id);
            return (
              <button
                key={p.id}
                onClick={() => toggle(p.id)}
                disabled={running}
                className={`chip border px-3 py-1.5 ${
                  on
                    ? "border-[var(--dark)] bg-[var(--brand)] text-[var(--brand-ink)]"
                    : "border-[var(--line)] bg-white text-gray-500"
                }`}
              >
                {on ? "✓ " : ""}
                {p.label}
              </button>
            );
          })}
        </div>

        <label className="mb-6 flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={staticOnly}
            onChange={(e) => setStaticOnly(e.target.checked)}
            disabled={running}
            className="mt-0.5 h-4 w-4 accent-[var(--brand)]"
          />
          <span>
            Static posts only (no videos)
            <span className="block text-xs text-[var(--muted)]">
              Note: search returns mostly reels, so this is usually sparse or empty.
            </span>
          </span>
        </label>

        <Button onClick={onPull} disabled={running || selected.length === 0}>
          {running ? "Pulling…" : "Start pulling posts"}
        </Button>

        {running && stage && (
          <div className="mt-5 flex items-center gap-3 text-sm text-gray-600">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-gray-300 border-t-[var(--dark)]" />
            {stage}
          </div>
        )}
      </div>

      {run && !running && (
        <div className="card mt-5 p-6">
          <div className="mb-3 flex items-center gap-2">
            <Badge tone="green">Pull complete</Badge>
            <span className="text-xs text-[var(--muted)]">
              {new Date(run.ran_at).toLocaleString()}
            </span>
          </div>
          {/* Debug funnel: pulled -> in pool -> in 24h window -> candidates -> trends */}
          <div className="flex flex-wrap gap-6">
            <Stat label="Query" value={`#${run.query}`} />
            <Stat label="Posts pulled" value={String(run.total_posts)} />
            {run.static_posts != null && (
              <Stat label="Static posts" value={String(run.static_posts)} />
            )}
            {run.pool_posts != null && (
              <Stat label="In pool (kept)" value={String(run.pool_posts)} />
            )}
            {run.posts_in_window != null && (
              <Stat
                label={`In ${windowLabel(run.window_hours)} window`}
                value={String(run.posts_in_window)}
              />
            )}
            {run.candidates_built != null && (
              <Stat label="Candidates" value={String(run.candidates_built)} />
            )}
            {run.rejected_blacklisted ? (
              <Stat label="Blacklisted" value={String(run.rejected_blacklisted)} />
            ) : null}
            <Stat label="Trends detected" value={String(run.trends_detected)} />
          </div>
          {run.posts_in_window === 0 && run.total_posts > 0 && (
            <p className="mt-3 text-xs text-amber-700">
              ⚠ {run.total_posts} posts pulled, but 0 fall in the {windowLabel(run.window_hours)}{" "}
              window — widen the detection window (try “All time”) to form trends.
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            {Object.entries(run.posts_pulled).map(([p, n]) => (
              <Badge key={p} tone="neutral">
                {p}: {n}
              </Badge>
            ))}
          </div>
          <div className="mt-5">
            <Link href="/trends" className="btn-primary">
              View {run.trends_detected} trends →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-[var(--muted)]">{label}</div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}
