/**
 * Public runtime configuration. Only NEXT_PUBLIC_* values are allowed here —
 * they are embedded in the browser bundle, so never put secrets in them.
 */

export interface PublicEnv {
  /** Base URL of the FastAPI backend. */
  apiUrl: string;
  /** Supabase project URL; when absent, Supabase auth is disabled. */
  supabaseUrl: string | null;
  /** Supabase publishable (anon) key — safe for browsers by design. */
  supabaseAnonKey: string | null;
  /** Local development login through the backend's /dev/token endpoint. */
  devAuth: boolean;
  /** Show "Continue with Google" (only once the Google provider is enabled in Supabase). */
  googleAuth: boolean;
}

function readEnv(): PublicEnv {
  // Each variable must be referenced literally so Next.js can inline it at build time.
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || null;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || null;
  return {
    apiUrl: (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, ""),
    supabaseUrl,
    supabaseAnonKey,
    devAuth: process.env.NEXT_PUBLIC_DEV_AUTH === "true",
    googleAuth: process.env.NEXT_PUBLIC_GOOGLE_AUTH === "true",
  };
}

export const env: PublicEnv = readEnv();

/** True when a real Supabase project is configured. */
export const supabaseEnabled: boolean = Boolean(env.supabaseUrl && env.supabaseAnonKey);
