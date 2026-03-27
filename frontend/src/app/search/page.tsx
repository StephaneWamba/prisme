"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { searchVisual } from "../../lib/api";

export default function SearchPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await searchVisual(url.trim());
      setResults(data);
    } catch (e: any) {
      setError("Recherche impossible - verifiez que l'URL est publique.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ marginBottom: 40 }}>
        <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, letterSpacing: "-0.03em" }}>
          Recherche visuelle
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          Collez l'URL d'une image pour trouver les produits visuellement similaires
        </p>
      </div>

      {/* Input */}
      <div className="card" style={{ marginBottom: 32 }}>
        <div className="search-wrap" style={{ marginBottom: 16 }}>
          <input
            type="url"
            placeholder="https://example.com/image.jpg"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            style={{
              width: "100%",
              padding: "10px 0",
              fontSize: 14,
              border: "none",
              outline: "none",
              background: "transparent",
              color: "var(--text)",
            }}
          />
          <div className="search-line" />
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || !url.trim()}
          style={{
            padding: "10px 24px",
            background: loading || !url.trim() ? "var(--bg-muted)" : "var(--text)",
            color: loading || !url.trim() ? "var(--text-muted)" : "var(--bg)",
            border: "none",
            borderRadius: 8,
            fontSize: 14,
            fontWeight: 600,
            cursor: loading || !url.trim() ? "not-allowed" : "pointer",
            transition: "all 150ms ease",
          }}
        >
          {loading ? "Analyse en cours..." : "Rechercher"}
        </button>
      </div>

      {error && (
        <p style={{ color: "var(--severity-critical)", fontSize: 13, marginBottom: 24 }}>{error}</p>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 16 }}>
            {results.length} produits visuellement similaires
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 16 }}>
            {results.map((r) => (
              <Link key={r.ean} href={`/products/${r.ean}`} style={{ textDecoration: "none" }}>
                <div className="card" style={{ cursor: "pointer", padding: 12 }}>
                  <div
                    style={{
                      width: "100%",
                      aspectRatio: "1",
                      borderRadius: 8,
                      background: "var(--bg-muted)",
                      overflow: "hidden",
                      position: "relative",
                      marginBottom: 10,
                    }}
                  >
                    {r.thumbnail_url ? (
                      <Image src={r.thumbnail_url} alt="" fill style={{ objectFit: "cover" }} sizes="150px" />
                    ) : (
                      <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-faint)" }}>?</div>
                    )}
                  </div>
                  <p style={{ fontSize: 12, fontWeight: 600, lineHeight: 1.3, marginBottom: 4, overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                    {r.product_name ?? r.ean}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-faint)" }}>
                    Similarite: {((1 - r.distance) * 100).toFixed(0)}%
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
