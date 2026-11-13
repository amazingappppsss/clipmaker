/** Hand-drawn squiggle arrow (decorative). Color comes from `className` (text-*). */
export function Squiggle({ className = "", variant = 1 }: { className?: string; variant?: 1 | 2 }) {
  const path =
    variant === 1
      ? "M6 58 C 30 10, 62 10, 58 40 S 30 72, 52 76 S 96 50, 110 30"
      : "M8 20 C 40 70, 70 -10, 92 40 S 70 80, 112 60";
  const head = variant === 1 ? "M96 26 L111 29 L106 44" : "M98 52 L113 60 L100 70";
  return (
    <svg viewBox="0 0 120 90" fill="none" aria-hidden className={className}>
      <path d={path} stroke="currentColor" strokeWidth="9" strokeLinecap="round" />
      <path
        d={head}
        stroke="currentColor"
        strokeWidth="9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
