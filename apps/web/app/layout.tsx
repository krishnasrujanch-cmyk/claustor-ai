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
    default: "Claustor AI — Contract Intelligence Platform",
    template: "%s | Claustor AI",
  },
  description:
    "AI-powered contract analysis, risk detection, and obligation tracking. Upload contracts, ask questions, get instant insights. Built for legal, finance, and procurement teams.",
  keywords: [
    "contract analysis", "AI contract review", "contract intelligence",
    "legal AI", "contract management", "risk detection", "obligation tracking",
    "CLM", "contract lifecycle management", "legal technology",
    "contract copilot", "document analysis", "enterprise AI",
  ],
  authors: [{ name: "Claustor AI" }],
  creator: "Claustor AI",
  metadataBase: new URL("https://claustor.com"),
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://claustor.com",
    siteName: "Claustor AI",
    title: "Claustor AI — Contract Intelligence Platform",
    description: "Transform contracts into intelligence with AI. Instant risk analysis, obligation tracking, and cross-contract insights.",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Claustor AI" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Claustor AI — Contract Intelligence Platform",
    description: "Transform contracts into intelligence with AI.",
    images: ["/og-image.png"],
  },
  robots: { index: true, follow: true },
  verification: {
    google: "add-your-google-verification-code",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            name: "Claustor AI",
            applicationCategory: "BusinessApplication",
            description: "AI-powered contract intelligence platform for legal, finance, and procurement teams.",
            url: "https://claustor.com",
            operatingSystem: "Web",
            offers: {
              "@type": "AggregateOffer",
              priceCurrency: "USD",
              lowPrice: "0",
              highPrice: "99",
              offerCount: "4",
            },
          }),
        }}
      />
      <body className="antialiased">{children}</body>
    </html>
  );
}
