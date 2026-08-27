import type { VelocitySignals } from "@/lib/types";

const LABELS: Record<keyof VelocitySignals, string> = {
  spike_6hr: "6h spike",
  volume_24hr: "24h volume",
  engagement_acceleration: "engagement ↑",
  cross_platform: "cross-platform",
  creator_tier: "creator tier",
};

export function VelocitySignalsRow({ velocity }: { velocity: VelocitySignals }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {(Object.keys(LABELS) as (keyof VelocitySignals)[]).map((key) => (
        <span
          key={key}
          className={`chip ${
            velocity[key] ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-400"
          }`}
          title={velocity[key] ? "signal fired" : "not fired"}
        >
          {velocity[key] ? "✓" : "·"} {LABELS[key]}
        </span>
      ))}
    </div>
  );
}
