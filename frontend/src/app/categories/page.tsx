import { getCategories } from "../../lib/api";

export const revalidate = 120;

function scoreColor(s: number) {
  if (s >= 75) return "#10b981";
  if (s >= 50) return "#f59e0b";
  return "#dc2626";
}

export default async function CategoriesPage() {
  let categories = [];
  try {
    categories = await getCategories();
  } catch {
    // empty state
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, letterSpacing: "-0.03em" }}>
          Rayons
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          Classement par score catalogue - du plus degrade au meilleur
        </p>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--bg-subtle)" }}>
              {["Rayon", "Score catalogue", "Metadonnees", "Visuels", "Produits"].map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "12px 16px",
                    textAlign: "left",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {categories.map((cat, i) => (
              <tr
                key={cat.category}
                style={{ borderBottom: i < categories.length - 1 ? "1px solid var(--border)" : "none" }}
              >
                <td style={{ padding: "14px 16px", fontSize: 13, fontWeight: 500 }}>
                  {cat.category || "Non classe"}
                </td>
                <td style={{ padding: "14px 16px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div
                      style={{
                        width: 120,
                        height: 6,
                        borderRadius: 3,
                        background: "var(--bg-muted)",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        className="bar-fill"
                        style={{
                          width: `${cat.avg_catalog_score}%`,
                          height: "100%",
                          background: scoreColor(cat.avg_catalog_score),
                          borderRadius: 3,
                        }}
                      />
                    </div>
                    <span
                      style={{
                        fontSize: 13,
                        fontWeight: 700,
                        color: scoreColor(cat.avg_catalog_score),
                        minWidth: 28,
                      }}
                    >
                      {cat.avg_catalog_score}
                    </span>
                  </div>
                </td>
                <td style={{ padding: "14px 16px", fontSize: 13, color: "var(--score-text)", fontWeight: 600 }}>
                  {cat.avg_text_score}
                </td>
                <td style={{ padding: "14px 16px", fontSize: 13, color: "var(--score-visual)", fontWeight: 600 }}>
                  {cat.avg_visual_score}
                </td>
                <td style={{ padding: "14px 16px", fontSize: 13, color: "var(--text-muted)" }}>
                  {cat.product_count.toLocaleString("fr-FR")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
