"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { QualityReport } from "@/components/quality-report";
import { Badge } from "@/components/ui/badge";
import { fetchPackages } from "@/lib/api";
import type { ContentPackage } from "@/lib/types";

const ASPECT_BOX: Record<string, string> = {
  "1:1": "aspect-square",
  "9:16": "aspect-[9/16]",
  "16:9": "aspect-video",
  "4:5": "aspect-[4/5]",
};

const STATUS_TONE = { generating: "amber", ready: "blue", approved: "green", rejected: "red" } as const;

export default function GeneratedPage() {
  const [packages, setPackages] = useState<ContentPackage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPackages()
      .then(setPackages)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-2xl font-bold">Generated Content</h1>
        <p className="text-sm text-[var(--muted)]">
          Step 3 — the posts generated from approved trends. Open one to approve or refine.
        </p>
      </header>

      {loading ? (
        <p className="text-sm text-[var(--muted)]">Loading…</p>
      ) : packages.length === 0 ? (
        <div className="card p-10 text-center">
          <p className="mb-4 text-sm text-[var(--muted)]">
            Nothing generated yet — approve a trend to generate content.
          </p>
          <Link href="/trends" className="btn-primary">
            Go to Trends
          </Link>
        </div>
      ) : (
        <div className="space-y-6">
          {packages.map((pkg) => (
            <div key={pkg.id} className="card p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold">#{pkg.trend_hashtag}</h2>
                  <Badge tone={STATUS_TONE[pkg.status]}>{pkg.status}</Badge>
                  <span className="text-xs text-[var(--muted)]">
                    {pkg.variants.length} variants
                  </span>
                </div>
                <Link href={`/trends/${pkg.trend_id}`} className="btn-ghost">
                  Open to review
                </Link>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {pkg.variants.map((v, i) => (
                  <div key={v.id} className="rounded-lg border border-[var(--line)] p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-xs font-semibold">Variant {i + 1}</span>
                      {v.status === "approved" && <Badge tone="green">approved</Badge>}
                      {v.status === "rejected" && <Badge tone="red">rejected</Badge>}
                    </div>
                    <div
                      className={`mb-2 flex ${
                        ASPECT_BOX[v.image_prompt.aspect_ratio] ?? "aspect-square"
                      } w-full items-center justify-center rounded-md border border-dashed border-gray-300 bg-gray-50 text-[11px] text-gray-400`}
                    >
                      image {v.image_prompt.aspect_ratio}
                    </div>
                    <p className="text-sm">{v.caption.caption}</p>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      {v.caption.hashtags.slice(0, 4).map((h) => (
                        <span key={h} className="text-[11px] text-sky-600">
                          {h}
                        </span>
                      ))}
                    </div>
                    <p className="mt-1 text-[11px] font-semibold text-gray-900">▸ {v.caption.cta}</p>
                    <div className="mt-2">
                      <QualityReport quality={v.quality} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
