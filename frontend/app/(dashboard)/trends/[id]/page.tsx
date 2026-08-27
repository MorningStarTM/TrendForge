"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { GeneratedContentView } from "@/components/generated-content";
import { PostThumb } from "@/components/post-thumb";
import { ScoreBar } from "@/components/score-bar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { VelocitySignalsRow } from "@/components/velocity-signals";
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

  if (loading) return <p className="text-sm text-[var(--muted)]">Loading…</p>;
  if (!trend) return <p className="text-sm text-red-600">Trend not found.</p>;

  return (
    <div>
      <Link href="/trends" className="text-sm text-[var(--muted)] hover:underline">
        ← Trends
      </Link>

      {/* Trend context */}
      <div className="card mt-3 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold">#{trend.hashtags[0]}</h1>
              {trend.category && <Badge tone="brand">{trend.category.replace("_", " ")}</Badge>}
              {trend.urgency && <Badge tone="amber">{trend.urgency.replace("_", " ")}</Badge>}
              {trend.status === "approved" && <Badge tone="green">approved</Badge>}
              {trend.status === "rejected" && <Badge tone="red">rejected</Badge>}
            </div>
            {trend.hashtags.length > 1 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {trend.hashtags.map((h) => (
                  <span key={h} className="text-xs text-sky-600">
                    #{h}
                  </span>
                ))}
              </div>
            )}
            {trend.trend_summary && (
              <p className="mt-2 max-w-2xl text-sm text-gray-600">{trend.trend_summary}</p>
            )}
            {trend.brand_angle && (
              <div className="mt-3 rounded-lg border-l-4 border-[var(--brand)] bg-[#fafae1] p-3 text-sm text-gray-900">
                <span className="font-bold">Brand angle: </span>
                {trend.brand_angle}
              </div>
            )}
          </div>
          <div className="w-48 shrink-0 space-y-2">
            {trend.brand_fit_score != null ? (
              <>
                <ScoreBar label="Brand fit" value={trend.brand_fit_score} />
                <ScoreBar label="Relevance" value={trend.relevance_score ?? 0} />
              </>
            ) : (
              <div className="rounded-lg bg-gray-50 p-3 text-center">
                <div className="text-3xl font-extrabold tabular-nums">{trend.signals_passed}/5</div>
                <div className="text-[11px] text-[var(--muted)]">velocity signals</div>
                <div className="mt-2 text-sm font-semibold">
                  {(trend.avg_engagement_rate * 100).toFixed(2)}%
                </div>
                <div className="text-[11px] text-[var(--muted)]">avg engagement</div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-4">
          <VelocitySignalsRow velocity={trend.velocity} />
        </div>

        <div className="mt-4 border-t border-[var(--line)] pt-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
            Posts in this trend — review before generating
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            {trend.source_posts.map((post, i) => (
              <PostThumb key={i} post={post} />
            ))}
          </div>
        </div>
      </div>

      {/* Extracted content — the inputs that feed content generation */}
      {trend.generation_inputs && (
        <div className="card mt-6 p-6">
          <h2 className="mb-1 text-lg font-bold">Extracted content</h2>
          <p className="mb-4 text-xs text-[var(--muted)]">
            Tags, captions and audio pulled from the posts — passed to content generation to
            create the post.
          </p>
          <div className="space-y-4 text-sm">
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                Trending hashtags
              </div>
              <div className="flex flex-wrap gap-1.5">
                {trend.generation_inputs.trending_hashtags.map((h) => (
                  <Badge key={h} tone="brand">
                    #{h}
                  </Badge>
                ))}
              </div>
            </div>
            {trend.generation_inputs.trending_audio.length > 0 && (
              <div>
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Audio / songs
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {trend.generation_inputs.trending_audio.map((a) => (
                    <Badge key={a} tone="neutral">
                      🎵 {a}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            <div>
              <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                Sample captions
              </div>
              <ul className="space-y-1">
                {trend.generation_inputs.captions.map((c, i) => (
                  <li key={i} className="rounded-md bg-gray-50 p-2 text-gray-700">
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Content generation (Bedrock) */}
      <div className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-bold">Generated content</h2>
          <Button onClick={onGenerate} disabled={busy}>
            {busy
              ? "Generating…"
              : generated
                ? "Regenerate"
                : "Generate content"}
          </Button>
        </div>

        {error && (
          <div className="card mb-4 border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
        )}

        {busy && (
          <div className="card flex items-center gap-3 p-6 text-sm text-gray-600">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-[var(--dark)]" />
            Classifying with Haiku and writing captions + image prompts with Sonnet… (~15s)
          </div>
        )}

        {!busy && !generated && (
          <div className="card p-8 text-center text-sm text-[var(--muted)]">
            Generate on-brand caption + image-prompt variants from this trend, via AWS Bedrock
            (Haiku classification → Sonnet captions & image prompts).
          </div>
        )}

        {!busy && generated && <GeneratedContentView content={generated} />}
      </div>
    </div>
  );
}
