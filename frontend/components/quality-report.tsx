import { Badge } from "@/components/ui/badge";
import type { GateAction, QualityGate } from "@/lib/types";

const ACTION_TONE: Record<GateAction, "green" | "amber" | "blue" | "red"> = {
  pass: "green",
  flag: "amber",
  regenerate_image: "blue",
  reject: "red",
};

const ACTION_LABEL: Record<GateAction, string> = {
  pass: "Passed quality gate",
  flag: "Flagged — review",
  regenerate_image: "Needs image regen",
  reject: "Rejected by gate",
};

export function QualityReport({ quality }: { quality: QualityGate }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-gray-50 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Quality gate
        </span>
        <Badge tone={ACTION_TONE[quality.action]}>{ACTION_LABEL[quality.action]}</Badge>
      </div>
      <ul className="space-y-1">
        {quality.checks.map((check) => (
          <li key={check.name} className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5">
              <span className={check.passed ? "text-emerald-600" : "text-red-600"}>
                {check.passed ? "✓" : "✕"}
              </span>
              <span className="text-gray-600">{check.name.replace(/_/g, " ")}</span>
            </span>
            {check.reason && <span className="text-gray-400">{check.reason}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
