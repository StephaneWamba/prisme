"use client";

interface ScoreGaugeProps {
  score: number;
  label: string;
  color?: string;
  size?: number;
}

function scoreColor(s: number) {
  if (s >= 75) return "#10b981";
  if (s >= 50) return "#f59e0b";
  return "#dc2626";
}

export default function ScoreGauge({ score, label, color, size = 120 }: ScoreGaugeProps) {
  const c = color ?? scoreColor(score);
  const r = (size - 16) / 2;
  const circ = 2 * Math.PI * r;
  const arcLen = circ * 0.75; // 3/4 circle
  const fill = arcLen * (score / 100);
  const gap = arcLen - fill;
  const rotation = 135; // start from bottom-left

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <svg width={size} height={size} style={{ transform: `rotate(${rotation}deg)` }}>
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--bg-muted)"
          strokeWidth={8}
          strokeDasharray={`${arcLen} ${circ - arcLen + 0.001}`}
          strokeLinecap="round"
        />
        {/* Value */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={c}
          strokeWidth={8}
          strokeDasharray={`${fill} ${gap + (circ - arcLen)}`}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 800ms ease" }}
        />
      </svg>
      <div style={{ marginTop: -size * 0.4, textAlign: "center", pointerEvents: "none" }}>
        <div style={{ fontSize: size * 0.22, fontWeight: 700, color: c, letterSpacing: "-0.03em", lineHeight: 1 }}>
          {score}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500, marginTop: 2 }}>
          {label}
        </div>
      </div>
    </div>
  );
}
