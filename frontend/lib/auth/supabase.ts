"use client";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { create } from "zustand";
import { USE_MOCKS } from "@/lib/api/client";

/**
 * Google sign-in through Supabase Auth (B06 §1). Three modes:
 * - `supabase`: NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_ANON_KEY are set (Vercel, B0.3 part A).
 * - `mock`: NEXT_PUBLIC_USE_MOCKS=1; "signing in" sets a fake user so the MSW flow can be tested.
 * - `off`: neither; the local API runs with `auth.mode: off`, so everyone is the local user.
 * The anon key is public by design; no secret ever reaches the browser.
 */
export type AuthMode = "supabase" | "mock" | "off";

const URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const ANON = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const AUTH_MODE: AuthMode = USE_MOCKS ? "mock" : URL && ANON ? "supabase" : "off";

let client: SupabaseClient | null = null;
export function supabase(): SupabaseClient | null {
  if (AUTH_MODE !== "supabase") return null;
  client ??= createClient(URL, ANON, { auth: { persistSession: true, flowType: "pkce" } });
  return client;
}

export interface AuthUser {
  id: string;
  email: string | null;
  name: string | null;
}

interface AuthState {
  mode: AuthMode;
  ready: boolean;
  user: AuthUser | null;
  token: string | null;
  init: () => void;
  signIn: (next?: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const MOCK_USER: AuthUser = { id: "mock-user", email: "you@example.com", name: "You" };
const MOCK_KEY = "fs_mock_session";

function readMock(): boolean {
  try {
    return sessionStorage.getItem(MOCK_KEY) === "1";
  } catch {
    return false;
  }
}

export const useAuth = create<AuthState>()((set, get) => ({
  mode: AUTH_MODE,
  ready: AUTH_MODE === "off",
  user: AUTH_MODE === "off" ? { id: "local-dev", email: null, name: null } : null,
  token: null,
  init: () => {
    const { mode } = get();
    if (mode === "mock") {
      set({ ready: true, user: readMock() ? MOCK_USER : null, token: readMock() ? "mock-token" : null });
      return;
    }
    const sb = supabase();
    if (!sb) return;
    void sb.auth.getSession().then(({ data }) => {
      const s = data.session;
      set({
        ready: true,
        token: s?.access_token ?? null,
        user: s ? { id: s.user.id, email: s.user.email ?? null, name: (s.user.user_metadata?.full_name as string) ?? null } : null,
      });
    });
    sb.auth.onAuthStateChange((_event, s) => {
      set({
        token: s?.access_token ?? null,
        user: s ? { id: s.user.id, email: s.user.email ?? null, name: (s.user.user_metadata?.full_name as string) ?? null } : null,
      });
    });
  },
  signIn: async (next = "/upload") => {
    const { mode } = get();
    if (mode === "mock") {
      try {
        sessionStorage.setItem(MOCK_KEY, "1");
      } catch {
        /* storage blocked: the session lasts until reload */
      }
      set({ user: MOCK_USER, token: "mock-token" });
      return;
    }
    const sb = supabase();
    if (!sb) return;
    await sb.auth.signInWithOAuth({ provider: "google", options: { redirectTo: `${window.location.origin}${next}` } });
  },
  signOut: async () => {
    const { mode } = get();
    if (mode === "mock") {
      try {
        sessionStorage.removeItem(MOCK_KEY);
      } catch {
        /* nothing to clear */
      }
      set({ user: null, token: null });
      return;
    }
    await supabase()?.auth.signOut();
    set({ user: null, token: null });
  },
}));
