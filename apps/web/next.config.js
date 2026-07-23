/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.API_URL || "http://localhost:8000"}/api/v1/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },

  images: {
    domains: ["claustor.com", "lh3.googleusercontent.com"],
  },

  env: {
    NEXT_PUBLIC_APP_URL: process.env.APP_URL || "http://localhost:3000",
    NEXT_PUBLIC_API_URL: process.env.API_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
