import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable strict mode
  reactStrictMode: true,

  // API proxy to FastAPI backend
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.API_URL || "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },

  // Security headers
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },

  // Image domains
  images: {
    domains: ["claustor.com", "lh3.googleusercontent.com"],
  },

  // Environment variables exposed to browser
  env: {
    NEXT_PUBLIC_APP_URL: process.env.APP_URL || "http://localhost:3000",
    NEXT_PUBLIC_API_URL: process.env.API_URL || "http://localhost:8000",
  },
};

export default nextConfig;
