"use client";
import { useState, useEffect, useCallback } from "react";
import { getProducts, type Product } from "../../lib/api";
import ProductCard from "../../components/ProductCard";

const PER_PAGE = 30;

export default function ProductsPage() {
  const [items, setItems] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [maxScore, setMaxScore] = useState<number | undefined>(undefined);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    try {
      const data = await getProducts({ page: p, per_page: PER_PAGE, min_score: minScore, max_score: maxScore });
      setItems(data.items);
      setTotal(data.total);
      setPage(p);
    } finally {
      setLoading(false);
    }
  }, [minScore, maxScore]);

  useEffect(() => { load(1); }, [load]);

  const filtered = filter
    ? items.filter((p) =>
        p.product_name?.toLowerCase().includes(filter.toLowerCase()) ||
        p.categories?.toLowerCase().includes(filter.toLowerCase())
      )
    : items;

  const totalPages = Math.ceil(total / PER_PAGE);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "40px 24px" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "clamp(22px, 3vw, 32px)", fontWeight: 700, letterSpacing: "-0.03em" }}>
          Catalogue
        </h1>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 6 }}>
          {total.toLocaleString("fr-FR")} produits
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <div className="search-wrap" style={{ flex: 1, minWidth: 200 }}>
          <input
            type="text"
            placeholder="Filtrer par nom ou rayon..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
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
        <select
          onChange={(e) => {
            const v = e.target.value;
            if (v === "all") { setMinScore(undefined); setMaxScore(undefined); }
            else if (v === "low") { setMinScore(undefined); setMaxScore(49); }
            else if (v === "mid") { setMinScore(50); setMaxScore(74); }
            else if (v === "high") { setMinScore(75); setMaxScore(undefined); }
          }}
          style={{
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid var(--border)",
            fontSize: 13,
            background: "var(--bg)",
            color: "var(--text)",
            cursor: "pointer",
          }}
        >
          <option value="all">Tous les scores</option>
          <option value="low">Score faible (0-49)</option>
          <option value="mid">Score moyen (50-74)</option>
          <option value="high">Bon score (75+)</option>
        </select>
      </div>

      {/* Grid */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 60, color: "var(--text-muted)", fontSize: 14 }}>
          Chargement...
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: 16,
            marginBottom: 32,
          }}
        >
          {filtered.map((p) => (
            <ProductCard key={p.ean} product={p} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 6, alignItems: "center" }}>
          <button
            onClick={() => load(page - 1)}
            disabled={page === 1}
            style={{
              padding: "6px 12px",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              background: "var(--bg)",
              cursor: page === 1 ? "not-allowed" : "pointer",
              color: page === 1 ? "var(--text-faint)" : "var(--text)",
            }}
          >
            Prec.
          </button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            const start = Math.max(1, Math.min(page - 2, totalPages - 4));
            const p = start + i;
            return (
              <button
                key={p}
                onClick={() => load(p)}
                style={{
                  width: 32,
                  height: 32,
                  border: "1px solid",
                  borderColor: p === page ? "var(--text)" : "var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                  background: p === page ? "var(--text)" : "var(--bg)",
                  color: p === page ? "var(--bg)" : "var(--text)",
                  cursor: "pointer",
                  fontWeight: p === page ? 600 : 400,
                }}
              >
                {p}
              </button>
            );
          })}
          <button
            onClick={() => load(page + 1)}
            disabled={page === totalPages}
            style={{
              padding: "6px 12px",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 13,
              background: "var(--bg)",
              cursor: page === totalPages ? "not-allowed" : "pointer",
              color: page === totalPages ? "var(--text-faint)" : "var(--text)",
            }}
          >
            Suiv.
          </button>
        </div>
      )}
    </div>
  );
}
