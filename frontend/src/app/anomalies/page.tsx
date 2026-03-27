import { getAnomalies } from "../../lib/api";
import AnomalyBadge from "../../components/AnomalyBadge";

export const revalidate = 0;

const TYPE_LABELS: Record<string, string> = {
  COMPLETENESS_DROP: "Chute de completude",
  COHERENCE_ISSUE: "Probleme de coherence",
  STATISTICAL_OUTLIER: "Valeur aberrante",
};

const METRIC_LABELS: Record<string, string> = {
  completeness_product_name: "Nom produit",
  completeness_brands: "Marques",
  completeness_categories: "Categories",
  completeness_ingredients: "Ingredients",
  completeness_nutriscore: "Nutriscore",
  completeness_quantity: "Quantite",
  completeness_packaging: "Conditionnement",
  coherence_nutriscore_with_ingredients: "Coherence Nutriscore",
  avg_length_product_name: "Longueur nom produit",
};

export default async function AnomaliesPage() {
  let anomalies: import("../../lib/api").Anomaly[] = [];
  try {
    anomalies = await getAnomalies();
  } catch {
    // empty state
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, letterSpacing: "-0.03em" }}>
          Alertes
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          Anomalies detectees sur les 7 derniers jours
        </p>
      </div>

      {anomalies.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "60px 24px", color: "var(--text-muted)" }}>
          <p style={{ fontSize: 32, marginBottom: 12 }}>-</p>
          <p style={{ fontSize: 14 }}>Aucune anomalie detectee</p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {anomalies.map((a) => (
            <div key={a.anomaly_id} className="card" style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
              <div style={{ flexShrink: 0, paddingTop: 2 }}>
                <AnomalyBadge severity={a.severity} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                  {METRIC_LABELS[a.metric_name] ?? a.metric_name}
                </p>
                <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 8 }}>{a.description}</p>
                <div style={{ display: "flex", gap: 16, fontSize: 12, color: "var(--text-faint)" }}>
                  <span>{TYPE_LABELS[a.anomaly_type] ?? a.anomaly_type}</span>
                  {a.z_score !== undefined && a.z_score !== null && (
                    <span>Z = {a.z_score.toFixed(2)}</span>
                  )}
                  {a.expected_value !== undefined && a.expected_value !== null && (
                    <span>Attendu: {a.expected_value.toFixed(1)}</span>
                  )}
                  <span>Observe: {a.observed_value?.toFixed(1)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
