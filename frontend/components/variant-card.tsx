"use client";

import { useState } from "react";

import { QualityReport } from "@/components/quality-report";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ContentVariant } from "@/lib/types";

const ASPECT_BOX: Record<string, string> = {
  "1:1": "aspect-square",
  "9:16": "aspect-[9/16]",
  "16:9": "aspect-video",
  "4:5": "aspect-[4/5]",
};

export function VariantCard({
  variant,
  index,
  onApprove,
  onReject,
  onRefine,
  busy,
}: {
  variant: ContentVariant;
  index: number;
  onApprove: (v: ContentVariant) => void;
  onReject: (v: ContentVariant) => void;
  onRefine: (v: ContentVariant, notes: string) => void;
  busy?: boolean;
}) {
  const [refining, setRefining] = useState(false);
  const [notes, setNotes] = useState("");
  const { caption, image_prompt } = variant;

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-2.5">
        <span className="text-sm font-semibold">Variant {index + 1}</span>
        <div className="flex items-center gap-1.5">
          <Badge tone="neutral">{caption.tone}</Badge>
          <Badge tone="blue">{caption.language}</Badge>
          <Badge tone="neutral">{caption.market}</Badge>
          {variant.status === "approved" && <Badge tone="green">approved</Badge>}
          {variant.status === "rejected" && <Badge tone="red">rejected</Badge>}
        </div>
      </div>

      <div className="grid gap-4 p-4 md:grid-cols-[180px_1fr]">
        {/* Image mockup placeholder (real image comes from Module 15 later) */}
        <div>
          <div
            className={`flex ${
              ASPECT_BOX[image_prompt.aspect_ratio] ?? "aspect-square"
            } w-full items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 text-center text-[11px] text-gray-400`}
          >
            image {image_prompt.aspect_ratio}
            <br />
            (generated later)
          </div>
          {image_prompt.text_overlay && (
            <p className="mt-1 text-center text-[11px] text-[var(--muted)]">
              overlay: “{image_prompt.text_overlay}”
            </p>
          )}
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-sm">{caption.caption}</p>
            <div className="mt-1.5 flex flex-wrap gap-1">
              {caption.hashtags.map((h) => (
                <span key={h} className="text-xs text-sky-600">
                  {h}
                </span>
              ))}
            </div>
            <p className="mt-1 text-xs font-semibold text-gray-900">▸ CTA: {caption.cta}</p>
          </div>

          <details className="text-xs">
            <summary className="cursor-pointer text-[var(--muted)]">Image prompt</summary>
            <div className="mt-1 space-y-1 rounded-lg bg-gray-50 p-2 text-gray-600">
              <p>
                <span className="font-semibold">Positive:</span> {image_prompt.positive_prompt}
              </p>
              <p>
                <span className="font-semibold">Negative:</span> {image_prompt.negative_prompt}
              </p>
              {image_prompt.style_reference && (
                <p>
                  <span className="font-semibold">Style:</span> {image_prompt.style_reference}
                </p>
              )}
            </div>
          </details>

          <QualityReport quality={variant.quality} />
        </div>
      </div>

      {variant.status === "pending" && (
        <div className="border-t border-[var(--line)] px-4 py-3">
          {refining ? (
            <div className="space-y-2">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="What should change? (e.g. too generic, wrong tone, funnier)"
                className="input"
                rows={2}
              />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" onClick={() => setRefining(false)} disabled={busy}>
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    onRefine(variant, notes);
                    setRefining(false);
                    setNotes("");
                  }}
                  disabled={busy || !notes.trim()}
                >
                  Regenerate with notes
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setRefining(true)} disabled={busy}>
                Refine
              </Button>
              <Button variant="danger" onClick={() => onReject(variant)} disabled={busy}>
                Reject
              </Button>
              <Button onClick={() => onApprove(variant)} disabled={busy}>
                Approve
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
