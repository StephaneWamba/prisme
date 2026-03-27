interface AnomalyBadgeProps {
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
}

const LABELS: Record<string, string> = {
  CRITICAL: "Critique",
  HIGH: "Elevee",
  MEDIUM: "Moderee",
  LOW: "Faible",
};

export default function AnomalyBadge({ severity }: AnomalyBadgeProps) {
  return (
    <span className={`severity-badge severity-${severity}`}>
      {LABELS[severity] ?? severity}
    </span>
  );
}
