// Inline stroke icons (no icon library — keeps the bundle self-contained).
// All inherit `currentColor` and a 1.75 stroke for a consistent 2026 look.

type P = { className?: string };

function Svg({ children, className }: P & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className ?? "h-5 w-5"}
      aria-hidden
    >
      {children}
    </svg>
  );
}

export const Icon = {
  Discover: (p: P) => (
    <Svg {...p}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3-3" />
      <path d="M11 8v6M8 11h6" />
    </Svg>
  ),
  Trends: (p: P) => (
    <Svg {...p}>
      <path d="M3 17l6-6 4 4 7-7" />
      <path d="M17 8h4v4" />
    </Svg>
  ),
  Brand: (p: P) => (
    <Svg {...p}>
      <path d="M4 5a2 2 0 0 1 2-2h12v18H6a2 2 0 0 1-2-2z" />
      <path d="M8 3v18" />
    </Svg>
  ),
  Settings: (p: P) => (
    <Svg {...p}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.17V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 8 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 3.6 15H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9 1.65 1.65 0 0 0 4.27 7.18l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6h.09A1.65 1.65 0 0 0 11 3.09V3a2 2 0 0 1 4 0v.09A1.65 1.65 0 0 0 16 4.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 20.4 9v.09c.14.31.4.55.71.66" />
    </Svg>
  ),
  Logout: (p: P) => (
    <Svg {...p}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <path d="M16 17l5-5-5-5M21 12H9" />
    </Svg>
  ),
  Upload: (p: P) => (
    <Svg {...p}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M17 8l-5-5-5 5M12 3v12" />
    </Svg>
  ),
  Download: (p: P) => (
    <Svg {...p}>
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5M12 15V3" />
    </Svg>
  ),
  Image: (p: P) => (
    <Svg {...p}>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <circle cx="9" cy="9" r="1.5" />
      <path d="m21 15-5-5L5 21" />
    </Svg>
  ),
  Sparkles: (p: P) => (
    <Svg {...p}>
      <path d="M12 3l1.8 4.7L18.5 9l-4.7 1.8L12 15l-1.8-4.2L5.5 9l4.7-1.3z" />
      <path d="M19 15l.7 1.8L21.5 17l-1.8.7L19 19l-.7-1.3L16.5 17l1.8-.2z" />
    </Svg>
  ),
  Trash: (p: P) => (
    <Svg {...p}>
      <path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M10 11v6M14 11v6" />
    </Svg>
  ),
  Refresh: (p: P) => (
    <Svg {...p}>
      <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
      <path d="M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16" />
      <path d="M3 21v-5h5" />
    </Svg>
  ),
  Bolt: (p: P) => (
    <Svg {...p}>
      <path d="M13 2 4 14h7l-1 8 9-12h-7z" />
    </Svg>
  ),
  Check: (p: P) => (
    <Svg {...p}>
      <path d="M20 6 9 17l-5-5" />
    </Svg>
  ),
  External: (p: P) => (
    <Svg {...p}>
      <path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    </Svg>
  ),
  Arrow: (p: P) => (
    <Svg {...p}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Svg>
  ),
  Back: (p: P) => (
    <Svg {...p}>
      <path d="M19 12H5M11 6l-6 6 6 6" />
    </Svg>
  ),
  Heart: (p: P) => (
    <Svg {...p}>
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z" />
    </Svg>
  ),
  Comment: (p: P) => (
    <Svg {...p}>
      <path d="M21 11.5a8.4 8.4 0 0 1-9 8 9 9 0 0 1-4-.9L3 20l1.4-4a8.4 8.4 0 0 1 3.6-11.5 8.4 8.4 0 0 1 12 3.9 8.4 8.4 0 0 1 1 3.1z" />
    </Svg>
  ),
  Play: (p: P) => (
    <Svg {...p}>
      <path d="M6 4l14 8-14 8z" />
    </Svg>
  ),
  Music: (p: P) => (
    <Svg {...p}>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </Svg>
  ),
  File: (p: P) => (
    <Svg {...p}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </Svg>
  ),
};
