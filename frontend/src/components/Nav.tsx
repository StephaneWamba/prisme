"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Tableau de bord" },
  { href: "/categories", label: "Rayons" },
  { href: "/anomalies", label: "Alertes" },
  { href: "/products", label: "Catalogue" },
  { href: "/search", label: "Recherche visuelle" },
  { href: "/reports", label: "Rapports" },
];

export default function Nav() {
  const [open, setOpen] = useState(false);
  const path = usePathname();

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "rgba(255,255,255,0.9)",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
        height: 60,
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "0 24px",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Link href="/" style={{ textDecoration: "none" }}>
          <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text)" }}>
            prisme
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex" style={{ gap: 4 }}>
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              style={{
                fontSize: 13,
                fontWeight: 500,
                padding: "6px 12px",
                borderRadius: 8,
                textDecoration: "none",
                color: path === l.href ? "var(--text)" : "var(--text-muted)",
                background: path === l.href ? "var(--bg-muted)" : "transparent",
                transition: "all 150ms ease",
              }}
            >
              {l.label}
            </Link>
          ))}
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden"
          onClick={() => setOpen(!open)}
          style={{ background: "none", border: "none", cursor: "pointer", padding: 8 }}
          aria-label="Menu"
        >
          <div style={{ width: 20, display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ height: 1.5, background: "var(--text)", display: "block", transition: "all 200ms", transform: open ? "rotate(45deg) translateY(5.5px)" : "none" }} />
            <span style={{ height: 1.5, background: "var(--text)", display: "block", opacity: open ? 0 : 1, transition: "all 200ms" }} />
            <span style={{ height: 1.5, background: "var(--text)", display: "block", transition: "all 200ms", transform: open ? "rotate(-45deg) translateY(-5.5px)" : "none" }} />
          </div>
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div style={{ background: "var(--bg)", borderBottom: "1px solid var(--border)", padding: "8px 24px 16px" }}>
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              style={{
                display: "block",
                padding: "10px 0",
                fontSize: 14,
                fontWeight: 500,
                color: path === l.href ? "var(--accent)" : "var(--text)",
                textDecoration: "none",
                borderBottom: "1px solid var(--border)",
              }}
            >
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </nav>
  );
}
