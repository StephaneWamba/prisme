import { getCatalogHealth } from "../lib/api";
import ScoreGauge from "../components/ScoreGauge";
import Link from "next/link";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

export const revalidate = 120;

export default async function HomePage() {
  let health = { catalog_score: 0, text_score: 0, visual_score: 0, product_count: 0 };
  let evolution: Array<{ date: string; catalog_score: number; text_score: number; visual_score: number }> = [];

  try {
    const data = await getCatalogHealth();
    health = data.health;
    evolution = data.evolution;
  } catch {
    // Show skeleton state
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <h1 style={{ fontSize: "clamp(24px, 4vw, 36px)", fontWeight: 700, letterSpacing: "-0.03em" }}>
          Tableau de bord
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          {health.product_count.toLocaleString("fr-FR")} produits analyses - Open Food Facts France
        </p>
      </div>

      {/* Score gauges */}
      <div
        className="card"
        style={{
          display: "flex",
          justifyContent: "space-around",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 32,
          marginBottom: 24,
          padding: "40px 24px",
        }}
      >
        <ScoreGauge score={health.catalog_score} label="Score catalogue" size={140} />
        <ScoreGauge score={health.text_score} label="Metadonnees" color="var(--score-text)" size={120} />
        <ScoreGauge score={health.visual_score} label="Assets visuels" color="var(--score-visual)" size={120} />
      </div>

      {/* Evolution chart */}
      {evolution.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 20, color: "var(--text-muted)" }}>
            EVOLUTION 30 JOURS
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={evolution}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "var(--text-faint)" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ fontSize: 11, fill: "var(--text-faint)" }}
                tickLine={false}
                axisLine={false}
                width={28}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line dataKey="catalog_score" stroke="#10b981" strokeWidth={2} dot={false} name="Catalogue" />
              <Line dataKey="text_score" stroke="var(--score-text)" strokeWidth={1.5} dot={false} name="Texte" />
              <Line dataKey="visual_score" stroke="var(--score-visual)" strokeWidth={1.5} dot={false} name="Visuel" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Quick links */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
        {[
          { href: "/categories", label: "Rayons par score", desc: "Classement des categories" },
          { href: "/anomalies", label: "Alertes actives", desc: "Anomalies detectees" },
          { href: "/products", label: "Catalogue complet", desc: "Tous les produits" },
          { href: "/reports", label: "Rapport Gemini", desc: "Analyse IA quotidienne" },
        ].map((item) => (
          <Link key={item.href} href={item.href} style={{ textDecoration: "none" }}>
            <div
              className="card"
              style={{ cursor: "pointer", transition: "border-color 150ms ease" }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-strong)")}
              onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)")}
            >
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>{item.label}</p>
              <p style={{ fontSize: 12, color: "var(--text-muted)" }}>{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
