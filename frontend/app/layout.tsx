import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VOXLORE STUDIO — AI Video Generator",
  description:
    "VOXLORE STUDIO: Generate cinematic AI-narrated videos for YouTube and Instagram. Two channels: The Inner Citadel (Stoic Philosophy) and neuralbaba_empire (Tech Concept Explainer). Powered by advanced AI — fully automated pipeline.",
  keywords: [
    "AI video generator", "stoic philosophy", "tech explainer",
    "YouTube automation", "AI content creation", "voxlore studio",
    "The Inner Citadel", "neuralbaba_empire", "automated video",
    "concept explainer", "AI narration"
  ],
  openGraph: {
    title: "VOXLORE STUDIO",
    description: "Multi-channel AI video generation — Stoic Philosophy + Tech Explainer",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "VOXLORE STUDIO",
    description: "Generate cinematic AI videos for YouTube and Instagram automatically.",
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
          href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700;900&family=Inter:wght@300;400;500;600;700;800&family=Orbitron:wght@400;700;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
