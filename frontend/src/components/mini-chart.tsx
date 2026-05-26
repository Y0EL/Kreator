export function MiniChart({ points, height = 110 }: { points: number[]; height?: number }) {
  if (!points || points.length < 2) {
    return (
      <div className="flex h-[110px] items-center justify-center text-xs text-faint">
        Tren belum cukup data, balik lagi besok.
      </div>
    );
  }
  const w = 320;
  const h = height;
  const pad = 6;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const dx = (w - 2 * pad) / (points.length - 1);
  const xy = points.map((p, i) => [pad + i * dx, h - pad - ((p - min) / span) * (h - 2 * pad)]);
  const line = xy.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const area = `${line} L ${xy[xy.length - 1][0].toFixed(1)} ${h - pad} L ${pad} ${h - pad} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full text-accent" preserveAspectRatio="none" style={{ height }}>
      <path d={area} fill="currentColor" opacity="0.12" />
      <path d={line} fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
