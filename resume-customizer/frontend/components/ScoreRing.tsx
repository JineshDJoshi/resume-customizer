export default function ScoreRing({ value, label, tone = "accent" }: { value: number; label: string; tone?: "accent" | "muted" }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className="ring" role="img" aria-label={`${label}: ${pct} percent`}>
      <svg width="68" height="68" viewBox="0 0 68 68" aria-hidden="true">
        <circle cx="34" cy="34" r={r} className="ring-track" />
        <circle
          cx="34" cy="34" r={r}
          className={`ring-value ${tone}`}
          strokeDasharray={c}
          strokeDashoffset={c - (c * pct) / 100}
          transform="rotate(-90 34 34)"
        />
      </svg>
      <span className="ring-num">{pct}</span>
      <span className="ring-label">{label}</span>
    </div>
  );
}
