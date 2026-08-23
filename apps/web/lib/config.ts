/**
 * Claustor AI — API Configuration
 * Uses NODE_ENV to switch between prod and dev URLs
 */
const isProd = process.env.NODE_ENV === 'production';

export const API_URL = isProd
  ? 'https://claustor-api-433747726821.asia-south1.run.app'
  : 'http://localhost:8000';

export const APP_URL = isProd
  ? 'https://claustor.com'
  : 'http://localhost:3000';

export const AUTH0_DOMAIN = isProd
  ? 'claustor.us.auth0.com'
  : 'dev-npbzjekxb7145tlz.us.auth0.com';

export const AUTH0_CLIENT_ID = isProd
  ? 'QGasMsTsqtJZBl23ZZhfcPFGx0lmS4Cb'
  : 'iBmGugaJH0WVuEgngdu2nsYxsvrHPCgu';

export const RAZORPAY_KEY_ID = isProd
  ? 'rzp_live_TSlbohAjzYuldw'
  : 'rzp_test_TK6rtv8V0IZoxU';
