"use client";

/** Sign-in: email magic link + Google (Supabase), or instant local login in dev mode. */
import { Mail } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/lib/auth/auth-provider";

/** Only allow same-site relative redirects (prevents open-redirect abuse). */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/dashboard";
}

export function LoginForm() {
  const { mode, status, signInWithEmail, signInWithGoogle } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkSent, setLinkSent] = useState(false);

  useEffect(() => {
    if (status === "signed_in") router.replace(next);
  }, [status, router, next]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await signInWithEmail(email.trim(), next);
      if (result === "link_sent") setLinkSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="spotlight grid min-h-dvh place-items-center px-4 py-10">
      <div className="animate-pop relative w-full max-w-sm rounded-[1.5rem] border border-line bg-surface p-8 shadow-[var(--shadow-float)]">
        <Logo />
        <h1 className="mt-8 text-4xl font-extrabold tracking-tight">Let&apos;s make shorts.</h1>
        <p className="mt-1 text-sm text-muted">
          Sign in or create an account — it&apos;s the same step.
        </p>

        {mode === "none" ? (
          <div className="mt-6">
            <Alert tone="error">
              Sign-in isn&apos;t configured. Set the Supabase keys (or enable dev login) — see the
              setup guide in README.md.
            </Alert>
          </div>
        ) : linkSent ? (
          <div className="mt-6">
            <Alert tone="success">
              Check <strong>{email}</strong> for a sign-in link. You can close this tab.
            </Alert>
          </div>
        ) : (
          <>
            {mode === "supabase" ? (
              <>
                <Button
                  variant="secondary"
                  className="mt-6 w-full"
                  onClick={() =>
                    void signInWithGoogle(next).catch((e: Error) => setError(e.message))
                  }
                >
                  Continue with Google
                </Button>
                <div className="my-5 flex items-center gap-3 text-xs text-muted">
                  <span className="h-px flex-1 bg-line" /> or{" "}
                  <span className="h-px flex-1 bg-line" />
                </div>
              </>
            ) : (
              <div className="mt-6">
                <Alert tone="info">Development login — no password or email is sent.</Alert>
              </div>
            )}
            <form onSubmit={(e) => void onSubmit(e)} className="mt-4 space-y-3">
              <label className="block">
                <span className="text-sm font-medium">Email</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="mt-1.5 h-12 w-full rounded-2xl border border-line-strong bg-canvas px-4 outline-none focus:border-violet"
                />
              </label>
              <Button type="submit" className="w-full" size="lg" loading={busy}>
                <Mail className="size-4" aria-hidden />
                {mode === "supabase" ? "Email me a sign-in link" : "Continue"}
              </Button>
            </form>
          </>
        )}
        {error ? (
          <div className="mt-4">
            <Alert tone="error">{error}</Alert>
          </div>
        ) : null}
      </div>
    </div>
  );
}
