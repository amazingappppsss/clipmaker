"use client";

/**
 * Authentication context.
 *
 * Modes:
 * - "supabase": real Supabase Auth (magic link + Google). Production.
 * - "dev":      local login via the backend's /dev/token (NEXT_PUBLIC_DEV_AUTH=true, dev only).
 * - "none":     nothing configured — sign-in is impossible and the UI says so.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getSupabase } from "@/lib/auth/supabase-client";
import { env, supabaseEnabled } from "@/lib/env";
import { fetchDevToken } from "@/services/account";
import { setTokenGetter } from "@/services/api-client";

export type AuthMode = "supabase" | "dev" | "none";
export type AuthStatus = "loading" | "signed_in" | "signed_out";

export interface AuthUser {
  id: string;
  email: string | null;
}

export interface AuthContextValue {
  mode: AuthMode;
  status: AuthStatus;
  user: AuthUser | null;
  /** Supabase: sends a magic link. Dev: signs in immediately. */
  signInWithEmail: (email: string, redirectPath: string) => Promise<"link_sent" | "signed_in">;
  signInWithGoogle: (redirectPath: string) => Promise<void>;
  /**
   * Supabase email + password. Sends no email when "Confirm email" is off in Supabase, so it is
   * not affected by email rate limits. Returns "check_email" if confirmation is still required.
   */
  passwordAuth: (
    mode: "sign_in" | "sign_up",
    email: string,
    password: string,
  ) => Promise<"signed_in" | "check_email">;
  signOut: () => Promise<void>;
}

const DEV_TOKEN_KEY = "clipmaker.devToken";
const AuthContext = createContext<AuthContextValue | null>(null);

const authMode: AuthMode = supabaseEnabled ? "supabase" : env.devAuth ? "dev" : "none";

/** localStorage can throw (private mode, blocked storage) — never let that break auth. */
function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable: session lasts for this tab only */
  }
}

interface DevClaims {
  sub: string;
  email?: string;
  exp: number;
}

function decodeDevToken(token: string): DevClaims | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    const claims = JSON.parse(json) as DevClaims;
    return claims.exp * 1000 > Date.now() ? claims : null;
  } catch {
    return null;
  }
}

function absoluteRedirect(path: string): string {
  return `${window.location.origin}${path.startsWith("/") ? path : "/dashboard"}`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [devToken, setDevToken] = useState<string | null>(null);

  // Restore the session on mount and follow Supabase auth changes.
  useEffect(() => {
    if (authMode === "supabase") {
      const supabase = getSupabase();
      if (!supabase) return;
      const apply = (session: { user: { id: string; email?: string } } | null): void => {
        setUser(session ? { id: session.user.id, email: session.user.email ?? null } : null);
        setStatus(session ? "signed_in" : "signed_out");
      };
      void supabase.auth.getSession().then(({ data }) => apply(data.session));
      const { data } = supabase.auth.onAuthStateChange((_event, session) => apply(session));
      return () => data.subscription.unsubscribe();
    }
    const stored = authMode === "dev" ? readStorage(DEV_TOKEN_KEY) : null;
    const claims = stored ? decodeDevToken(stored) : null;
    // Hydrating from browser storage must happen after mount (storage is unavailable on the server).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDevToken(claims ? stored : null);
    setUser(claims ? { id: claims.sub, email: claims.email ?? null } : null);
    setStatus(claims ? "signed_in" : "signed_out");
    return undefined;
  }, []);

  // Give the API client a way to fetch a fresh token for every request.
  useEffect(() => {
    setTokenGetter(async () => {
      if (authMode === "supabase") {
        const { data } = (await getSupabase()?.auth.getSession()) ?? { data: { session: null } };
        return data.session?.access_token ?? null;
      }
      return devToken && decodeDevToken(devToken) ? devToken : null;
    });
  }, [devToken]);

  const signInWithEmail = useCallback(
    async (email: string, redirectPath: string): Promise<"link_sent" | "signed_in"> => {
      if (authMode === "supabase") {
        const supabase = getSupabase();
        if (!supabase) throw new Error("Sign-in is not configured.");
        const { error } = await supabase.auth.signInWithOtp({
          email,
          options: { emailRedirectTo: absoluteRedirect(redirectPath) },
        });
        if (error) throw new Error(error.message);
        return "link_sent";
      }
      if (authMode === "dev") {
        const { access_token, user_id } = await fetchDevToken(email);
        writeStorage(DEV_TOKEN_KEY, access_token);
        setDevToken(access_token);
        setUser({ id: user_id, email });
        setStatus("signed_in");
        return "signed_in";
      }
      throw new Error("Sign-in is not configured on this server.");
    },
    [],
  );

  const signInWithGoogle = useCallback(async (redirectPath: string): Promise<void> => {
    const supabase = getSupabase();
    if (!supabase) throw new Error("Google sign-in requires Supabase to be configured.");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: absoluteRedirect(redirectPath) },
    });
    if (error) throw new Error(error.message);
  }, []);

  const passwordAuth = useCallback(
    async (
      mode: "sign_in" | "sign_up",
      email: string,
      password: string,
    ): Promise<"signed_in" | "check_email"> => {
      const supabase = getSupabase();
      if (!supabase) throw new Error("Password sign-in requires Supabase to be configured.");
      const { data, error } =
        mode === "sign_in"
          ? await supabase.auth.signInWithPassword({ email, password })
          : await supabase.auth.signUp({ email, password });
      if (error) throw new Error(error.message);
      return data.session ? "signed_in" : "check_email";
    },
    [],
  );

  const signOut = useCallback(async (): Promise<void> => {
    if (authMode === "supabase") await getSupabase()?.auth.signOut();
    writeStorage(DEV_TOKEN_KEY, null);
    setDevToken(null);
    setUser(null);
    setStatus("signed_out");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      mode: authMode,
      status,
      user,
      signInWithEmail,
      signInWithGoogle,
      passwordAuth,
      signOut,
    }),
    [status, user, signInWithEmail, signInWithGoogle, passwordAuth, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the auth context; throws when used outside <AuthProvider>. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
