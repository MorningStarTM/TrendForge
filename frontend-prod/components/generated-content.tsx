"use client";

import { useState } from "react";

import { Icon } from "@/components/icons";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { Spinner } from "@/components/ui/spinner";
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
      {/* Classification summary */}
      <div className="card p-5">
        <div className="mb-2.5 flex flex-wrap items-center gap-2">
          <span className="eyebrow">AI classification</span>
          {c.category && <Chip tone="brand">{c.category.replace(/_/g, " ")}</Chip>}
          {c.brand_fit_score != null && <Chip tone="green">brand fit {c.brand_fit_score}</Chip>}
          {c.relevance_score != null && <Chip tone="blue">relevance {c.relevance_score}</Chip>}
          {c.urgency && <Chip tone="amber">{c.urgency.replace(/_/g, " ")}</Chip>}
        </div>
        {c.trend_summary && <p className="text-sm text-gray-600">{c.trend_summary}</p>}
        {c.brand_angle && (
          <div className="mt-3 rounded-xl border-l-4 border-[var(--brand)] bg-[#fcfcdf] p-3 text-sm text-gray-900">
            <span className="font-semibold">Brand angle — </span>
            {c.brand_angle}
          </div>
        )}
        {c.risk_flags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {c.risk_flags.map((f) => (
              <Chip key={f} tone="red">
                {f}
              </Chip>
            ))}
          </div>
        )}
      </div>

      {/* Caption + image variants */}
      {content.variants.map((v, i) => {
        const img = images[i];
        return (
          <div key={i} className="card overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--line-2)] px-5 py-3">
              <span className="text-sm font-bold">Variant {i + 1}</span>
              <div className="flex flex-wrap items-center gap-1.5">
                <Chip tone="neutral">{v.tone}</Chip>
                <Chip tone="blue">{v.language}</Chip>
                <Chip tone="neutral">{v.market}</Chip>
                {v.valid ? <Chip tone="green">valid</Chip> : <Chip tone="amber">flagged</Chip>}
              </div>
            </div>

            <div className="grid gap-5 p-5 md:grid-cols-[1fr_260px]">
              {/* Caption */}
              <div className="space-y-3">
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{v.caption}</p>
                {v.hashtags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {v.hashtags.map((h) => (
                      <span key={h} className="text-xs font-medium text-sky-600">
                        {h.startsWith("#") ? h : `#${h}`}
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-xs font-semibold text-gray-900">▸ {v.cta}</p>

                {v.image_prompt && (
                  <details className="text-xs">
                    <summary className="cursor-pointer select-none text-[var(--muted)] hover:text-[var(--ink)]">
                      Image prompt · {v.image_prompt.aspect_ratio}
                    </summary>
                    <div className="mt-1.5 space-y-1 rounded-xl bg-[var(--panel-2)] p-3 text-gray-600">
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
                          <span className="font-semibold">Overlay:</span>{" "}
                          {v.image_prompt.text_overlay}
                        </p>
                      )}
                    </div>
                  </details>
                )}

                {!v.valid && v.issues.length > 0 && (
                  <p className="text-xs text-amber-700">⚠ {v.issues.join("; ")}</p>
                )}
              </div>

              {/* Image generation panel */}
              {v.image_prompt && (
                <div className="flex flex-col">
                  <div className="relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-xl border border-dashed border-[var(--line)] bg-[var(--panel-2)]">
                    {img?.dataUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={img.dataUrl}
                        alt={`Variant ${i + 1} image`}
                        className="h-full w-full object-cover"
                      />
                    ) : img?.loading ? (
                      <div className="flex flex-col items-center gap-2 text-xs text-gray-500">
                        <Spinner />
                        Generating…
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-1.5 px-4 text-center text-gray-400">
                        <Icon.Image className="h-7 w-7" />
                        <span className="text-[11px]">No image yet</span>
                      </div>
                    )}
                  </div>

                  <div className="mt-2.5 flex gap-2">
                    {img?.dataUrl ? (
                      <>
                        <a
                          href={img.dataUrl}
                          download={`trendforge-variant-${i + 1}.png`}
                          className="flex-1"
                        >
                          <Button size="sm" className="w-full">
                            <Icon.Download className="h-4 w-4" /> Download
                          </Button>
                        </a>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onGenerateImage(i)}
                          title="Regenerate"
                        >
                          <Icon.Refresh className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        variant="dark"
                        className="w-full"
                        onClick={() => onGenerateImage(i)}
                        disabled={img?.loading}
                      >
                        <Icon.Sparkles className="h-4 w-4" />
                        {img?.loading ? "Generating…" : "Generate image"}
                      </Button>
                    )}
                  </div>
                  {img?.error && <p className="mt-1.5 text-[11px] text-red-600">⚠ {img.error}</p>}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
