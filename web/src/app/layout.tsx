import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Reci — Reciclaje inteligente en la PUCE",
    template: "%s · Reci",
  },
  description:
    "Robot autónomo de reciclaje para el campus PUCE Sede Manabí. Clasifica vidrio y plástico, te llama al punto más cercano y te recompensa por reciclar.",
  applicationName: "Reci",
  keywords: ["reciclaje", "PUCE", "Manabí", "IoT", "sistema experto", "robot"],
  authors: [{ name: "Equipo Reci — PUCE Manabí" }],
  manifest: "/manifest.webmanifest",
};

export const viewport: Viewport = {
  themeColor: "#0f9d58",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-cream text-ink">
        {children}
      </body>
    </html>
  );
}
