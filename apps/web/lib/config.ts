/**
 * Claustor AI — API Configuration
 * NEXT_PUBLIC_* vars are baked in at build time from .env.production
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";
export const AUTH0_DOMAIN = process.env.NEXT_PUBLIC_AUTH0_DOMAIN || "";
export const AUTH0_CLIENT_ID = process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID || "";
export const RAZORPAY_KEY_ID = process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || "";
