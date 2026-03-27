import { getProductDetail } from "../../../lib/api";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

export const revalidate = 0;

function scoreColor(s: number) {
  if (s >= 75) return "#10b981";
  if (s >= 50) return "#f59e0b";
  return "#dc2626";
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <span style={{ fontSize: 12, color: "var(--text-muted)", width: 80, flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 6, borderRadius: 3, background: "var(--bg-muted)", overflow: "hidden" }}>
        <div
          className="bar-fill"
          style={{ width: `${value}%`, height: "100%", background: color, borderRadius: 3 }}
        />
      </div>
      <span style={{ fontSize: 12, fontWeight: 700, color, width: 28, textAlign: "right" }}>{value}</span>
    </div>
  );
}

export default async function ProductPage({ params }: { params: { ean: string } }) {
  let product;
  try {
    product = await getProductDetail(params.ean);
  } catch {
    notFound();
  }
  if (!product) notFound();

  const cat = product.categories?.split(",")[0]?.trim() ?? "Autre";
  const catalog_score = product.catalog_score ?? 0;

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 24px" }}>
      <Link
        href="/products"
        style={{ fontSize: 13, color: "var(--text-muted)", textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 4, marginBottom: 24 }}
      >
        - Retour au catalogue
      </Link>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 32, alignItems: "start" }}>
        {/* Image */}
        <div>
          <div
            style={{
              width: "100%",
              aspectRatio: "1",
              borderRadius: 16,
              background: "var(--bg-muted)",
              overflow: "hidden",
              position: "relative",
            }}
          >
            {product.thumbnail_url_512 || product.thumbnail_url_256 || product.image_url ? (
              <Image
                src={product.thumbnail_url_512 ?? product.thumbnail_url_256 ?? product.image_url!}
                alt={product.product_name ?? ""}
                fill
                style={{ objectFit: "cover" }}
                sizes="300px"
              />
            ) : (
              <div
                style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 48, color: "var(--text-faint)" }}
              >
                ?
              </div>
            )}
          </div>

          {/* Vision label */}
          {product.primary_object_label && (
            <div
              style={{
                marginTop: 12,
                padding: "8px 12px",
                background: "var(--bg-subtle)",
                borderRadius: 8,
                fontSize: 12,
                color: "var(--text-muted)",
              }}
            >
              Detection: <strong>{product.primary_object_label}</strong>
            </div>
          )}
        </div>

        {/* Details */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div>
            <p style={{ fontSize: 12, color: "var(--text-faint)", marginBottom: 4 }}>{cat}</p>
            <h1 style={{ fontSize: "clamp(20px, 3vw, 28px)", fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.2 }}>
              {product.product_name ?? product.ean}
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 6 }}>EAN: {product.ean}</p>
          </div>

          {/* Global score */}
          <div className="card" style={{ display: "flex", alignItems: "center", gap: 20 }}>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 16,
                background: `${scoreColor(catalog_score)}20`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 22,
                fontWeight: 800,
                color: scoreColor(catalog_score),
                letterSpacing: "-0.03em",
                flexShrink: 0,
              }}
            >
              {catalog_score}
            </div>
            <div>
              <p style={{ fontSize: 14, fontWeight: 600 }}>Score catalogue</p>
              <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
                {catalog_score >= 75 ? "Bonne qualite" : catalog_score >= 50 ? "Qualite moyenne" : "Fiche incomplete"}
              </p>
            </div>
          </div>

          {/* Score breakdown */}
          <div className="card">
            <h2 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 16 }}>
              DETAIL DES SCORES
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <ScoreBar label="Metadonnees" value={product.text_score ?? 0} color="var(--score-text)" />
              <ScoreBar label="Visuels" value={product.visual_score ?? 0} color="var(--score-visual)" />
              <ScoreBar label="Resolution" value={product.resolution_score ?? 0} color="#6b7280" />
              <ScoreBar label="Nettete" value={product.sharpness_score ?? 0} color="#6b7280" />
              <ScoreBar label="Centrage" value={product.centration_score ?? 0} color="#6b7280" />
            </div>
          </div>

          {/* Metadata */}
          <div className="card">
            <h2 style={{ fontSize: 12, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 16 }}>
              METADONNEES
            </h2>
            {[
              ["Marques", (product as any).brands],
              ["Categories", product.categories],
              ["Nutriscore", (product as any).nutriscore_grade],
              ["Quantite", (product as any).quantity],
              ["Conditionnement", (product as any).packaging],
            ].map(([label, value]) =>
              value ? (
                <div key={label as string} style={{ display: "flex", gap: 12, marginBottom: 8, fontSize: 13 }}>
                  <span style={{ color: "var(--text-muted)", width: 110, flexShrink: 0 }}>{label as string}</span>
                  <span style={{ color: "var(--text)" }}>{value as string}</span>
                </div>
              ) : null
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
