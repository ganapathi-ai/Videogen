import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "THE INNER CITADEL — Autonomous Stoic Video Generator",
  description:
    "Generate cinematic Stoic philosophy videos for YouTube automatically. Powered by AI — 100% free and open source.",
  keywords: ["stoic", "philosophy", "youtube", "video generator", "AI", "inner citadel"],
  openGraph: {
    title: "THE INNER CITADEL",
    description: "Autonomous Stoic video generation pipeline",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
