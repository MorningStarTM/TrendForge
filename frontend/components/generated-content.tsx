"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { generateVariantImage } from "@/lib/api";
import type { GeneratedContent } from "@/lib/types";

type ImageState = { loading: boolean; dataUrl?: string; error?: string };

export function GeneratedContentView({ content }: { content: GeneratedContent }) {
  const c = content.classification;
  const [images, setImages] = useState<Record<number, ImageState>>({});

  async function onGenerateImage(index: number) {
    setImages((s) => ({ ...s, [index]: { loading: true } }));
    try {
      const { data_url } = await generateVariantImage(content.trend_id, index);
      setImages((s) => ({ ...s, [index]: { loading: false, dataUrl: data_url } }));
    } catch (e) {
      setImages((s) => ({
        ...s,
        [index]: { loading: false, error: e instanceof Error ? e.message : "Failed" },
      }));
    }
  }

  return (
    <div className="space-y-4">
      {/* Haiku classification */}
      <div className="card p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold">AI classification</span>
          {c.category && <Badge tone="brand">{c.category.replace("_", " ")}</Badge>}
          {c.brand_fit_score != null && <Badge tone="green">brand fit {c.brand_fit_score}</Badge>}
          {c.relevance_score != null && <Badge tone="blue">relevance {c.relevance_score}</Badge>}
          {c.urgency && <Badge tone="amber">{c.urgency.replace("_", " ")}</Badge>}
        </div>
        {c.trend_summary && <p className="text-sm text-gray-600">{c.trend_summary}</p>}
        {c.brand_angle && (
          <div className="mt-2 rounded-lg border-l-4 border-[var(--brand)] bg-[#fafae1] p-2 text-sm text-gray-900">
            <span className="font-bold">Brand angle: </span>
            {c.brand_angle}
          </div>
        )}
        {c.risk_flags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {c.risk_flags.map((f) => (
              <Badge key={f} tone="red">
                {f}
              </Badge>
            ))}
          </div>
        )}
      </div>

      {/* Sonnet caption + image-prompt variants */}
      {content.variants.map((v, i) => {
        const img = images[i];
        return (
          <div key={i} className="card overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-2.5">
              <span className="text-sm font-semibold">Variant {i + 1}</span>
              <div className="flex items-center gap-1.5">
                <Badge tone="neutral">{v.tone}</Badge>
                <Badge tone="blue">{v.language}</Badge>
                <Badge tone="neutral">{v.market}</Badge>
                {v.valid ? <Badge tone="green">valid</Badge> : <Badge tone="amber">flagged</Badge>}
              </div>
            </div>
            <div className="space-y-3 p-4">
              <div>
                <p className="whitespace-pre-wrap text-sm">{v.caption}</p>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {v.hashtags.map((h) => (
                    <span key={h} className="text-xs text-sky-600">
                      {h}
                    </span>
                  ))}
                </div>
                <p className="mt-1 text-xs font-semibold text-gray-900">▸ {v.cta}</p>
              </div>

              {v.image_prompt && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-[var(--muted)]">
                    Image prompt · {v.image_prompt.aspect_ratio}
                  </summary>
                  <div className="mt-1 space-y-1 rounded-lg bg-gray-50 p-2 text-gray-600">
                    <p>
                      <span className="font-semibold">Positive:</span>{" "}
                      {v.image_prompt.positive_prompt}
                    </p>
                    <p>
                      <span className="font-semibold">Negative:</span>{" "}
                      {v.image_prompt.negative_prompt}
                    </p>
                    {v.image_prompt.text_overlay && (
                      <p>
                        <span className="font-semibold">Overlay:</span> {v.image_prompt.text_overlay}
                      </p>
                    )}
                  </div>
                </details>
              )}

              {!v.valid && v.issues.length > 0 && (
                <p className="text-xs text-amber-700">⚠ {v.issues.join("; ")}</p>
              )}

              {/* Image generation (Gemini nano banana) */}
              {v.image_prompt && (
                <div className="border-t border-[var(--line)] pt-3">
                  {img?.dataUrl ? (
                    <div className="space-y-2">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={img.dataUrl}
                        alt={`Generated image for variant ${i + 1}`}
                        className="w-full rounded-lg border border-[var(--line)]"
                      />
                      <div className="flex gap-2">
                        <a href={img.dataUrl} download={`trendforge-variant-${i + 1}.png`}>
                          <Button>Download image</Button>
                        </a>
                        <Button variant="ghost" onClick={() => onGenerateImage(i)}>
                          Regenerate
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <Button onClick={() => onGenerateImage(i)} disabled={img?.loading}>
                      {img?.loading ? "Generating image… (~10s)" : "Generate image"}
                    </Button>
                  )}
                  {img?.error && <p className="mt-2 text-xs text-red-600">⚠ {img.error}</p>}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
