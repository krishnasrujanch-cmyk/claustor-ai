import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Claustor — The AI-Powered Contract Intelligence Platform",
    template: "%s | Claustor",
  },
  description:
    "Claustor analyses your contracts in seconds. Extract clauses, score risk, track obligations — no legal team required.",
  keywords: ["contract intelligence", "AI contract review", "CLM", "contract analysis"],
  authors: [{ name: "Claustor AI" }],
  openGraph: {
    title: "Claustor — AI Contract Intelligence",
    description: "Transform contracts into intelligence with AI.",
    url: "https://claustor.com",
    siteName: "Claustor",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Claustor — AI Contract Intelligence",
    description: "Transform contracts into intelligence with AI.",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
