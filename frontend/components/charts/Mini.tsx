// Tiny SVG charts for tiles: they carry a shape, never an axis. The number next to them says what they show.

export function MiniBars({ values, label, tone = "var(--chart-1)" }: { values: number[]; label: string; tone?: string }) {
  const clean = values.filter((v) => Number.isFinite(v) && v >= 0);
  if (clean.length < 2) return null;
  const max = Math.max(...clean, 1);
  const w = 6;
  const gap = 3;
  const h = 32;
  return (
    <svg role="img" aria-label={label} viewBox={`0 0 ${clean.length * (w + gap)} ${h}`} className="h-8 w-full max-w-[120px]" preserveAspectRatio="none">
      {clean.map((v, i) => {
        const bh = Math.max(2, (v / max) * h);
        return <rect key={i} x={i * (w + gap)} y={h - bh} width={w} height={bh} rx="1.5" fill={tone} opacity={0.35 + 0.65 * (i / Math.max(1, clean.length - 1))} />;
      })}
    </svg>
  );
}

export function MiniLine({ values, label, tone = "var(--chart-1)" }: { values: number[]; label: string; tone?: string }) {
  const clean = values.filter((v) => Number.isFinite(v));
  if (clean.length < 2) return null;
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const span = max - min || 1;
  const w = 120;
  const h = 32;
  const pts = clean.map((v, i) => `${(i / (clean.length - 1)) * w},${h - 3 - ((v - min) / span) * (h - 6)}`);
  return (
    <svg role="img" aria-label={label} viewBox={`0 0 ${w} ${h}`} className="h-8 w-full max-w-[120px]" preserveAspectRatio="none">
      <polyline points={pts.join(" ")} fill="none" stroke={tone} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      <circle cx={pts[pts.length - 1].split(",")[0]} cy={pts[pts.length - 1].split(",")[1]} r="3" fill={tone} />
    </svg>
  );
}

/** A horizontal fill from 0 to 100 percent. */
export function MiniMeter({ value, label, tone = "var(--chart-1)" }: { value: number; label: string; tone?: string }) {
  if (!Number.isFinite(value)) return null;
  const v = Math.max(0, Math.min(100, value));
  return (
    <div role="img" aria-label={label} className="h-2 w-full max-w-[120px] overflow-hidden rounded-full bg-surface-2">
      <div className="h-full rounded-full" style={{ width: `${v}%`, background: tone, transition: "width 600ms var(--ease-out)" }} />
    </div>
  );
}
