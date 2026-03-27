"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

const STEPS = [
  {
    icon: "◎",
    title: "Tableau de bord",
    desc: "Score de qualite global du catalogue sur 100, evolution 30 jours, et acces rapide a chaque module.",
    href: "/",
  },
  {
    icon: "▤",
    title: "Catalogue",
    desc: "1 000 produits Open Food Facts classes par score. Filtrez par nom, rayon ou niveau de qualite.",
    href: "/products",
  },
  {
    icon: "◈",
    title: "Recherche visuelle",
    desc: "Collez l'URL d'une photo produit. CLIP analyse l'image et retrouve les articles visuellement similaires dans le catalogue.",
    href: "/search",
  },
  {
    icon: "⚠",
    title: "Alertes",
    desc: "Anomalies detectees automatiquement sur les metadonnees : valeurs manquantes, incoherences, doublons.",
    href: "/anomalies",
  },
  {
    icon: "◆",
    title: "Rapport Gemini",
    desc: "Analyse IA quotidienne generee par Gemini 2.5 Flash : resume executif, problemes critiques et recommandations.",
    href: "/reports",
  },
];

export default function WelcomeModal() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!localStorage.getItem("prisme_welcomed")) {
      setOpen(true);
    }
  }, []);

  function dismiss() {
    localStorage.setItem("prisme_welcomed", "1");
    setOpen(false);
  }

  if (!open) return null;

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
      onClick={(e) => e.target === e.currentTarget && dismiss()}
    >
      <div
        style={{
          background: "var(--bg)",
          border: "1px solid var(--border)",
          borderRadius: 20,
          padding: "40px 36px 32px",
          maxWidth: 480,
          width: "100%",
          position: "relative",
          animation: "fade-in 250ms ease forwards",
        }}
      >
        {/* Close */}
        <button
          onClick={dismiss}
          style={{
            position: "absolute",
            top: 16,
            right: 16,
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 18,
            color: "var(--text-faint)",
            lineHeight: 1,
            padding: "4px 8px",
          }}
        >
          x
        </button>

        {/* Step 0 : intro */}
        {step === 0 && (
          <div style={{ marginBottom: 32 }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 12 }}>
              Bienvenue sur
            </p>
            <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: "-0.04em", marginBottom: 12 }}>
              Prisme
            </h1>
            <p style={{ fontSize: 14, color: "var(--text-muted)", lineHeight: 1.6 }}>
              Plateforme d'audit qualite catalogue pour le retail FMCG.
              Prisme analyse 1 000 produits Open Food Facts sur deux dimensions :
              la completude des metadonnees et la qualite des visuels.
            </p>
          </div>
        )}

        {/* Steps 1-5 */}
        {step > 0 && (
          <div style={{ marginBottom: 32 }}>
            <p style={{ fontSize: 28, marginBottom: 16 }}>{current.icon}</p>
            <h2 style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 10 }}>
              {current.title}
            </h2>
            <p style={{ fontSize: 14, color: "var(--text-muted)", lineHeight: 1.65 }}>
              {current.desc}
            </p>
          </div>
        )}

        {/* Progress dots */}
        <div style={{ display: "flex", gap: 6, marginBottom: 28 }}>
          {STEPS.map((_, i) => (
            <button
              key={i}
              onClick={() => setStep(i + 1)}
              style={{
                width: i + 1 === step ? 20 : 6,
                height: 6,
                borderRadius: 3,
                border: "none",
                cursor: "pointer",
                background: i + 1 === step ? "var(--text)" : "var(--border-strong)",
                transition: "all 200ms ease",
                padding: 0,
              }}
            />
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 10 }}>
          {step === 0 ? (
            <>
              <button
                onClick={() => setStep(1)}
                style={{
                  flex: 1,
                  padding: "11px 0",
                  background: "var(--text)",
                  color: "var(--bg)",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Decouvrir le projet
              </button>
              <button
                onClick={dismiss}
                style={{
                  padding: "11px 20px",
                  background: "var(--bg-muted)",
                  color: "var(--text-muted)",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Passer
              </button>
            </>
          ) : isLast ? (
            <Link
              href={current.href}
              onClick={dismiss}
              style={{
                flex: 1,
                padding: "11px 0",
                background: "var(--text)",
                color: "var(--bg)",
                border: "none",
                borderRadius: 10,
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                textDecoration: "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              Acceder au tableau de bord
            </Link>
          ) : (
            <>
              <button
                onClick={() => setStep((s) => s + 1)}
                style={{
                  flex: 1,
                  padding: "11px 0",
                  background: "var(--text)",
                  color: "var(--bg)",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Suivant
              </button>
              <button
                onClick={() => setStep((s) => s - 1)}
                style={{
                  padding: "11px 20px",
                  background: "var(--bg-muted)",
                  color: "var(--text-muted)",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Retour
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
