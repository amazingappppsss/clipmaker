/** Lazily created browser Supabase client (null when Supabase is not configured). */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { env, supabaseEnabled } from "@/lib/env";

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (!supabaseEnabled || !env.supabaseUrl || !env.supabaseAnonKey) return null;
  client ??= createClient(env.supabaseUrl, env.supabaseAnonKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  return client;
}
