import Link from "next/link";
import Image from "next/image";
import type { Product } from "../lib/api";

function decodeHtml(str: string): string {
  return str
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#039;/g, "'");
}

function scoreClass(s: number) {
  if (s >= 75) return "score-high";
  if (s >= 50) return "score-mid";
  return "score-low";
}

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const cat = product.categories?.split(",")[0]?.trim() ?? "Autre";

  return (
    <Link href={`/products/${product.ean}`} style={{ textDecoration: "none" }}>
      <div
        className="card"
        style={{
          cursor: "pointer",
          transition: "border-color 150ms ease, box-shadow 150ms ease",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border-strong)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 16px rgba(0,0,0,0.06)";
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)";
          (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
        }}
      >
        {/* Thumbnail */}
        <div
          style={{
            width: "100%",
            aspectRatio: "1",
            borderRadius: 8,
            background: "var(--bg-muted)",
            overflow: "hidden",
            position: "relative",
          }}
        >
          {product.thumbnail_url_128 ? (
            <Image
              src={product.thumbnail_url_128}
              alt={product.product_name ?? ""}
              fill
              style={{ objectFit: "cover" }}
              sizes="160px"
            />
          ) : (
            <div
              style={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 28,
                color: "var(--text-faint)",
              }}
            >
              ?
            </div>
          )}
          {(product.has_anomaly_text || product.has_anomaly_visual) && (
            <div
              style={{
                position: "absolute",
                top: 6,
                right: 6,
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "var(--severity-critical)",
              }}
            />
          )}
        </div>

        {/* Info */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
          <p
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text)",
              lineHeight: 1.3,
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
            }}
          >
            {decodeHtml(product.product_name ?? product.ean)}
          </p>
          <p style={{ fontSize: 11, color: "var(--text-faint)", lineHeight: 1 }}>{cat}</p>
        </div>

        {/* Score */}
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className={`score-badge ${scoreClass(product.catalog_score)}`}>
            {product.catalog_score}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>score catalogue</span>
        </div>
      </div>
    </Link>
  );
}
