type Tone = "brand" | "neutral" | "green" | "amber" | "red" | "blue";

const TONES: Record<Tone, string> = {
  brand: "chip-brand",
  neutral: "chip-neutral",
  green: "chip-green",
  amber: "chip-amber",
  red: "chip-red",
  blue: "chip-blue",
};

export function Chip({
  tone = "neutral",
  children,
}: {
  tone?: Tone;
  children: React.ReactNode;
}) {
  return <span className={TONES[tone]}>{children}</span>;
}
