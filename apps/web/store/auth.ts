"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

const API_URL = "http://localhost:8000";

interface AuthUser {
  user_id: string;
  org_id: string;
  email: string;
  role: string;
  plan: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: { email: string; password: string; full_name: string; org_name: string }) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,

      login: async (email, password) => {
        set({ isLoading: true });
        try {
          const r = await fetch(`${API_URL}/api/v1/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });
          if (!r.ok) {
            const err = await r.json();
            throw new Error(err.detail || "Login failed");
          }
          const data = await r.json();
          set({ token: data.access_token });
          await get().loadUser();
        } finally {
          set({ isLoading: false });
        }
      },

      register: async (data) => {
        set({ isLoading: true });
        try {
          const r = await fetch(`${API_URL}/api/v1/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
          });
          if (!r.ok) {
            const err = await r.json();
            throw new Error(err.detail || "Registration failed");
          }
          const result = await r.json();
          set({ token: result.access_token });
          await get().loadUser();
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        set({ user: null, token: null });
        window.location.href = "/login";
      },

      loadUser: async () => {
        const token = get().token;
        if (!token) {
          set({ user: null });
          return;
        }
        try {
          const r = await fetch(`${API_URL}/api/v1/auth/me`, {
            headers: { "Authorization": `Bearer ${token}` },
          });
          if (!r.ok) {
            set({ user: null, token: null });
            return;
          }
          const user = await r.json();
          set({ user });
        } catch {
          set({ user: null, token: null });
        }
      },
    }),
    {
      name: "claustor-auth",
      partialize: (state) => ({ token: state.token }),
    }
  )
);
