import type { ReactNode } from "react";

type Tone = "neutral" | "brand" | "green" | "amber" | "red" | "blue";

const TONES: Record<Tone, string> = {
  neutral: "bg-gray-100 text-gray-700",
  brand: "bg-[var(--brand)] text-[var(--brand-ink)]",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-red-50 text-red-700",
  blue: "bg-sky-50 text-sky-700",
};

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className={`chip ${TONES[tone]}`}>{children}</span>;
}
