import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScoreBar } from "@/components/score-bar";
import { VelocitySignalsRow } from "@/components/velocity-signals";
import type { Trend } from "@/lib/types";

function platformSummary(platforms: Trend["platforms"]): string {
  return Object.entries(platforms)
    .map(([p, n]) => `${p} ${n}`)
    .join(" · ");
}

export function TrendCard({
  trend,
  onApprove,
  onReject,
  busy,
}: {
  trend: Trend;
  onApprove: (t: Trend) => void;
  onReject: (t: Trend) => void;
  busy?: boolean;
}) {
  const classified = trend.brand_fit_score != null; // Haiku detection has run
  const decided = trend.status !== "pending";

  return (
    <div className="card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Link href={`/trends/${trend.id}`} className="text-lg font-bold hover:underline">
              #{trend.hashtags[0]}
            </Link>
            {trend.category && <Badge tone="brand">{trend.category.replace("_", " ")}</Badge>}
            {trend.hashtags.length > 1 && (
              <span className="text-xs text-[var(--muted)]">
                +{trend.hashtags.length - 1} tags
              </span>
            )}
            {trend.status === "approved" && <Badge tone="green">approved</Badge>}
            {trend.status === "rejected" && <Badge tone="red">rejected</Badge>}
          </div>
          {trend.trend_summary ? (
            <p className="mt-2 max-w-2xl text-sm text-gray-600">{trend.trend_summary}</p>
          ) : (
            <p className="mt-2 text-sm text-gray-500">
              {trend.source_posts.length} source post
              {trend.source_posts.length === 1 ? "" : "s"} · detected by the rule engine
            </p>
          )}
          <p className="mt-1 text-xs text-[var(--muted)]">{platformSummary(trend.platforms)}</p>
        </div>

        <div className="w-44 shrink-0 space-y-2">
          {classified ? (
            <>
              <ScoreBar label="Brand fit" value={trend.brand_fit_score ?? 0} />
              <ScoreBar label="Relevance" value={trend.relevance_score ?? 0} />
            </>
          ) : (
            <div className="rounded-lg bg-gray-50 p-3 text-center">
              <div className="text-2xl font-extrabold tabular-nums">{trend.signals_passed}/5</div>
              <div className="text-[11px] text-[var(--muted)]">velocity signals</div>
            </div>
          )}
        </div>
      </div>

      {trend.source_posts.some((p) => p.thumbnail_url) && (
        <div className="mt-4 flex gap-2 overflow-x-auto">
          {trend.source_posts
            .filter((p) => p.thumbnail_url)
            .slice(0, 6)
            .map((p, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={i}
                src={p.thumbnail_url as string}
                alt="post"
                loading="lazy"
                referrerPolicy="no-referrer"
                className="h-16 w-16 shrink-0 rounded-md border border-[var(--line)] object-cover"
              />
            ))}
        </div>
      )}

      <div className="mt-4">
        <VelocitySignalsRow velocity={trend.velocity} />
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-[var(--line)] pt-4">
        <span className="text-xs text-[var(--muted)]">
          {trend.signals_passed}/5 signals · avg engagement{" "}
          {(trend.avg_engagement_rate * 100).toFixed(2)}%
        </span>
        {!classified || decided ? (
          <Link href={`/trends/${trend.id}`} className="btn-ghost">
            View details
          </Link>
        ) : (
          <div className="flex gap-2">
            <Button variant="danger" onClick={() => onReject(trend)} disabled={busy}>
              Reject
            </Button>
            <Button onClick={() => onApprove(trend)} disabled={busy}>
              Approve → Generate
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
