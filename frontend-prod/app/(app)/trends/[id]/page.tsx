"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { GeneratedContentView } from "@/components/generated-content";
import { Icon } from "@/components/icons";
import { PostThumb } from "@/components/post-thumb";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Spinner } from "@/components/ui/spinner";
import { fetchGenerated, fetchTrend, generateContent } from "@/lib/api";
import type { GeneratedContent, Trend } from "@/lib/types";

export default function TrendDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [trend, setTrend] = useState<Trend | null>(null);
  const [generated, setGenerated] = useState<GeneratedContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchTrend(id), fetchGenerated(id)])
      .then(([t, g]) => {
        setTrend(t);
        setGenerated(g);
      })
      .catch(() => setError("Trend not found"))
      .finally(() => setLoading(false));
  }, [id]);

  async function onGenerate() {
    setBusy(true);
    setError(null);
    try {
      setGenerated(await generateContent(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="skeleton h-64 rounded-2xl" />;
  if (!trend) return <p className="text-sm text-red-600">Trend not found.</p>;

  const inputs = trend.generation_inputs;

  return (
    <div className="space-y-6">
      <Link
        href="/trends"
        className="inline-flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--ink)]"
      >
        <Icon.Back className="h-4 w-4" /> All trends
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight">#{trend.hashtags[0]}</h1>
              {trend.category && <Chip tone="brand">{trend.category.replace(/_/g, " ")}</Chip>}
              {trend.urgency && <Chip tone="amber">{trend.urgency.replace(/_/g, " ")}</Chip>}
            </div>
            {trend.hashtags.length > 1 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {trend.hashtags.slice(1, 8).map((h) => (
                  <span key={h} className="text-xs font-medium text-sky-600">
                    #{h}
                  </span>
                ))}
              </div>
            )}
            {trend.trend_summary && (
              <p className="mt-3 max-w-2xl text-sm text-gray-600">{trend.trend_summary}</p>
            )}
            {trend.brand_angle && (
              <div className="mt-3 max-w-2xl rounded-xl border-l-4 border-[var(--brand)] bg-[#fcfcdf] p-3 text-sm text-gray-900">
                <span className="font-semibold">Brand angle — </span>
                {trend.brand_angle}
              </div>
            )}
          </div>

          <div className="flex shrink-0 gap-3">
            <Stat label="Posts" value={`${trend.source_posts.length}`} />
            {trend.brand_fit_score != null ? (
              <Stat label="Brand fit" value={`${trend.brand_fit_score}`} highlight />
            ) : (
              <Stat label="Signals" value={`${trend.signals_passed}/5`} highlight />
            )}
            <Stat label="Engagement" value={`${(trend.avg_engagement_rate * 100).toFixed(1)}%`} />
          </div>
        </div>
      </div>

      {/* Filtered posts */}
      <section>
        <h2 className="mb-1 text-base font-bold">Posts in this trend</h2>
        
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {trend.source_posts.map((post, i) => (
            <PostThumb key={i} post={post} />
          ))}
        </div>
      </section>

      {/* Extracted content */}
      {inputs && (
        <section className="card p-6">
          <h2 className="text-base font-bold">Extracted from these posts</h2>
          
          <div className="grid gap-5 md:grid-cols-3">
            <div>
              <span className="eyebrow">Trending hashtags</span>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {inputs.trending_hashtags.length ? (
                  inputs.trending_hashtags.map((h) => (
                    <Chip key={h} tone="brand">
                      #{h}
                    </Chip>
                  ))
                ) : (
                  <span className="text-xs text-[var(--faint)]">None</span>
                )}
              </div>
            </div>
            <div>
              <span className="eyebrow">Audio / songs</span>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {inputs.trending_audio.length ? (
                  inputs.trending_audio.map((a) => (
                    <span
                      key={a}
                      className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-700"
                    >
                      <Icon.Music className="h-3 w-3" /> {a}
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-[var(--faint)]">None detected</span>
                )}
              </div>
            </div>
            <div>
              <span className="eyebrow">Market</span>
              <div className="mt-2">
                <Chip tone="neutral">{inputs.market}</Chip>
              </div>
            </div>
          </div>
          {inputs.captions.length > 0 && (
            <div className="mt-5">
              <span className="eyebrow">Sample captions</span>
              <ul className="mt-2 space-y-1.5">
                {inputs.captions.slice(0, 4).map((c, i) => (
                  <li
                    key={i}
                    className="line-clamp-2 rounded-xl bg-[var(--panel-2)] p-2.5 text-sm text-gray-700"
                  >
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* Generation */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold">Generated content</h2>
            
          </div>
          <Button onClick={onGenerate} disabled={busy}>
            {busy ? (
              <>
                <Spinner /> Generating…
              </>
            ) : (
              <>
                <Icon.Sparkles className="h-4 w-4" />
                {generated ? "Regenerate" : "Generate content"}
              </>
            )}
          </Button>
        </div>

        {error && (
          <div className="card mb-4 border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {busy && (
          <div className="card flex items-center gap-3 p-6 text-sm text-gray-600">
            <Spinner />
            Classifying the trend and writing captions + image prompts…
          </div>
        )}

        {!busy && !generated && (
          <div className="card px-6 py-12 text-center text-sm text-[var(--muted)]">
            Generate caption and image variants tailored to this trend, then render and download
            images for the ones you like.
          </div>
        )}

        {!busy && generated && <GeneratedContentView content={generated} />}
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`min-w-[74px] rounded-xl border px-3 py-2 text-center ${
        highlight ? "border-[var(--brand-deep)] bg-[#fcfcdf]" : "border-[var(--line)] bg-[var(--panel-2)]"
      }`}
    >
      <div className="text-xl font-extrabold tabular-nums">{value}</div>
      <div className="text-[11px] font-medium text-[var(--muted)]">{label}</div>
    </div>
  );
}
