import { getLatestReport } from "../../lib/api";
import ScoreGauge from "../../components/ScoreGauge";

export const revalidate = 300;

export default async function ReportsPage() {
  let report = null;
  try {
    report = await getLatestReport();
  } catch {
    // no report yet
  }

  if (!report) {
    return (
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 24px" }}>
        <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 24 }}>
          Rapport Gemini
        </h1>
        <div className="card" style={{ textAlign: "center", padding: "60px 24px", color: "var(--text-muted)" }}>
          <p style={{ fontSize: 14 }}>Aucun rapport disponible. Lancez le pipeline pour generer le premier rapport.</p>
        </div>
      </div>
    );
  }

  const date = new Date(report.report_date).toLocaleDateString("fr-FR", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ marginBottom: 32 }}>
        <p style={{ fontSize: 12, color: "var(--text-faint)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Rapport du {date}
        </p>
        <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, letterSpacing: "-0.03em" }}>
          Rapport Gemini
        </h1>
      </div>

      {/* Scores */}
      <div
        className="card"
        style={{ display: "flex", justifyContent: "space-around", flexWrap: "wrap", gap: 24, marginBottom: 24, padding: "32px 24px" }}
      >
        <ScoreGauge score={report.catalog_score} label="Score catalogue" size={110} />
        <ScoreGauge score={report.text_score} label="Metadonnees" color="var(--score-text)" size={90} />
        <ScoreGauge score={report.visual_score} label="Visuels" color="var(--score-visual)" size={90} />
      </div>

      {/* Summary */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
          RESUME EXECUTIF
        </h2>
        <p style={{ fontSize: 15, lineHeight: 1.6, color: "var(--text)" }}>{report.executive_summary}</p>
      </div>

      {/* Critical issues */}
      {report.critical_issues?.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 12, fontWeight: 600, color: "var(--severity-critical)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
            PROBLEMES CRITIQUES
          </h2>
          <ul style={{ paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
            {report.critical_issues.map((issue, i) => (
              <li key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--severity-critical)", marginTop: 6, flexShrink: 0 }} />
                <span style={{ fontSize: 14, color: "var(--text)", lineHeight: 1.5 }}>{issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations?.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
            RECOMMANDATIONS
          </h2>
          <ol style={{ paddingLeft: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 10 }}>
            {report.recommendations.map((rec, i) => (
              <li key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                <span style={{ width: 22, height: 22, borderRadius: 6, background: "var(--bg-muted)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "var(--accent)", flexShrink: 0 }}>
                  {i + 1}
                </span>
                <span style={{ fontSize: 14, color: "var(--text)", lineHeight: 1.5 }}>{rec}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* Worst categories */}
      {report.worst_categories?.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
            RAYONS LES PLUS DEGRADEES
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {report.worst_categories.map((cat, i) => (
              <span
                key={i}
                style={{
                  padding: "4px 12px",
                  background: "var(--bg-muted)",
                  borderRadius: 20,
                  fontSize: 13,
                  color: "var(--text)",
                }}
              >
                {cat}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
