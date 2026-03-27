import type { Metadata } from "next";
import "./globals.css";
import Nav from "../components/Nav";
import WelcomeModal from "../components/WelcomeModal";

export const metadata: Metadata = {
  title: "Prisme - Audit qualite catalogue",
  description: "Plateforme d'audit qualite catalogue retail & FMCG",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <Nav />
        <WelcomeModal />
        <main style={{ minHeight: "calc(100vh - 60px)", position: "relative", zIndex: 1 }}>
          {children}
        </main>
      </body>
    </html>
  );
}
