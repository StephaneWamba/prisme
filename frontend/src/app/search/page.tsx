"use client";
import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { searchVisual } from "../../lib/api";

const EXAMPLES = [
  {
    label: "Fondue de poireaux",
    url: "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000112302614.jpg",
  },
  {
    label: "Bratwurst Schnecke",
    url: "https://storage.googleapis.com/prisme-assets/thumbnails/128/00001040.jpg",
  },
  {
    label: "Levure nutritionnelle",
    url: "https://storage.googleapis.com/prisme-assets/thumbnails/128/00001449.jpg",
  },
  {
    label: "Déli'soupe",
    url: "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000112407469.jpg",
  },
  {
    label: "Nut Butter Bar",
    url: "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000128100086.jpg",
  },
  {
    label: "Chocolat lait noisettes",
    url: "https://storage.googleapis.com/prisme-assets/thumbnails/128/0000130028030.jpg",
  },
];

function decodeHtml(str: string): string {
  return str
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#039;/g, "'");
}

export default function SearchPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [hasSearched, setHasSearched] = useState(false);

  // Rotate placeholder every 3s
  useEffect(() => {
    const t = setInterval(() => {
      setPlaceholderIdx((i) => (i + 1) % EXAMPLES.length);
    }, 3000);
    return () => clearInterval(t);
  }, []);

  const handleSearch = async (searchUrl?: string) => {
    const q = (searchUrl ?? url).trim();
    if (!q) return;
    if (searchUrl) setUrl(searchUrl);
    setLoading(true);
    setError("");
    setHasSearched(true);
    try {
      const data = await searchVisual(q);
      setResults(data);
    } catch {
      setError("");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 24px" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, letterSpacing: "-0.03em" }}>
          Recherche visuelle
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          Collez l'URL d'une photo produit — CLIP trouve les articles visuellement similaires dans les 1000 produits du catalogue.
        </p>
      </div>

      {/* Input card */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="search-wrap" style={{ marginBottom: 16 }}>
          <input
            type="url"
            placeholder={`Ex : ${EXAMPLES[placeholderIdx].label}`}
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
          onClick={() => handleSearch()}
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
          {loading ? "Analyse CLIP en cours..." : "Rechercher"}
        </button>
      </div>

      {/* Suggestion chips */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 32 }}>
        {EXAMPLES.map((ex) => (
          <button
            key={ex.label}
            onClick={() => handleSearch(ex.url)}
            style={{
              padding: "6px 14px",
              border: "1px solid var(--border)",
              borderRadius: 20,
              background: "transparent",
              color: "var(--text-muted)",
              fontSize: 12,
              cursor: "pointer",
              transition: "all 150ms ease",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border-strong)";
              (e.currentTarget as HTMLButtonElement).style.color = "var(--text)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)";
              (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)";
            }}
          >
            {ex.label}
          </button>
        ))}
      </div>

      {/* Zero results */}
      {hasSearched && !loading && results.length === 0 && !error && (
        <div className="card" style={{ textAlign: "center", padding: "40px 24px" }}>
          <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Aucun résultat</p>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 20 }}>
            L'image n'est pas accessible ou trop différente du catalogue.
          </p>
          <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
            {EXAMPLES.slice(0, 3).map((ex) => (
              <button
                key={ex.label}
                onClick={() => handleSearch(ex.url)}
                style={{
                  padding: "6px 14px",
                  border: "1px solid var(--border-strong)",
                  borderRadius: 20,
                  background: "transparent",
                  color: "var(--text)",
                  fontSize: 12,
                  cursor: "pointer",
                }}
              >
                Essayer : {ex.label}
              </button>
            ))}
          </div>
        </div>
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
                    {decodeHtml(r.product_name ?? r.ean)}
                  </p>
                  <p style={{ fontSize: 11, color: "var(--text-faint)" }}>
                    Similarité : {((1 - r.distance) * 100).toFixed(0)}%
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
