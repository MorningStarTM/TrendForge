import Link from "next/link";

import { Icon } from "@/components/icons";
import { Chip } from "@/components/ui/chip";
import type { Trend } from "@/lib/types";

export function TrendCard({ trend }: { trend: Trend }) {
  const cover = trend.source_posts.find((p) => p.thumbnail_url)?.thumbnail_url;
  const postCount = trend.source_posts.length;
  const engagement = (trend.avg_engagement_rate * 100).toFixed(1);

  return (
    <Link
      href={`/trends/${trend.id}`}
      className="card group flex overflow-hidden transition-shadow hover:shadow-[var(--shadow-md)]"
    >
      <div className="relative w-28 shrink-0 overflow-hidden bg-gray-100">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover}
            alt=""
            referrerPolicy="no-referrer"
            loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-gray-300">
            <Icon.Image className="h-6 w-6" />
          </div>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col justify-between p-4">
        <div>
          <div className="flex items-start justify-between gap-2">
            <h3 className="truncate text-base font-bold">#{trend.hashtags[0]}</h3>
            {trend.brand_fit_score != null ? (
              <Chip tone="green">fit {trend.brand_fit_score}</Chip>
            ) : (
              <Chip tone="brand">{trend.signals_passed}/5 signals</Chip>
            )}
          </div>
          {trend.trend_summary ? (
            <p className="mt-1 line-clamp-2 text-sm text-gray-600">{trend.trend_summary}</p>
          ) : (
            trend.hashtags.length > 1 && (
              <p className="mt-1 line-clamp-1 text-xs text-sky-600">
                {trend.hashtags.slice(1, 5).map((h) => `#${h}`).join("  ")}
              </p>
            )
          )}
        </div>

        <div className="mt-3 flex items-center gap-4 text-xs font-medium text-[var(--muted)]">
          <span>{postCount} posts</span>
          <span className="inline-flex items-center gap-1">
            <Icon.Heart className="h-3.5 w-3.5" /> {engagement}% eng.
          </span>
          {trend.category && <Chip tone="neutral">{trend.category.replace(/_/g, " ")}</Chip>}
          <Icon.Arrow className="ml-auto h-4 w-4 text-[var(--faint)] transition-transform group-hover:translate-x-0.5" />
        </div>
      </div>
    </Link>
  );
}
