import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      // ── Claustor Design Tokens ────────────────────
      colors: {
        primary: {
          DEFAULT: "#5B4BFF",
          hover:   "#4C3FE0",
          light:   "#EEF0FF",
        },
        secondary: "#3B82F6",
        accent: {
          ai:     "#06B6D4",
          purple: "#6366F1",
        },
        background: "#FAFBFC",
        surface: {
          DEFAULT: "#FFFFFF",
          alt:     "#F5F7FA",
        },
        border: "#E5E7EB",
        text: {
          heading: "#111827",
          body:    "#374151",
          muted:   "#6B7280",
        },
        success: "#22C55E",
        warning: "#F59E0B",
        error:   "#EF4444",
        info:    "#3B82F6",
      },

      // ── Typography ─────────────────────────────────
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },

      // ── Spacing (8px grid) ─────────────────────────
      spacing: {
        "0.5": "4px",
        "1":   "8px",
        "1.5": "12px",
        "2":   "16px",
        "2.5": "20px",
        "3":   "24px",
        "4":   "32px",
        "5":   "40px",
        "6":   "48px",
        "8":   "64px",
        "10":  "80px",
        "12":  "96px",
        "16":  "128px",
      },

      // ── Border Radius ──────────────────────────────
      borderRadius: {
        "sm":  "4px",
        "md":  "8px",
        "lg":  "12px",
        "xl":  "16px",
        "2xl": "24px",
      },

      // ── Shadows ────────────────────────────────────
      boxShadow: {
        "card": "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)",
        "dropdown": "0 4px 12px rgba(0,0,0,0.12)",
        "modal": "0 20px 60px rgba(0,0,0,0.15)",
      },
    },
  },
  plugins: [],
};

export default config;
