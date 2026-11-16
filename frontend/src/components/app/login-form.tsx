"use client";

/**
 * Sign-in page.
 * - Supabase: email + password (sign in / create account) — sends no email when "Confirm email"
 *   is off, so it is immune to email rate limits. Magic link remains as a fallback, and the
 *   Google button shows only when NEXT_PUBLIC_GOOGLE_AUTH=true (provider enabled in Supabase).
 * - Dev mode: instant local login (no password).
 */
import { Mail } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/lib/auth/auth-provider";
import { env } from "@/lib/env";

/** Only allow same-site relative redirects (prevents open-redirect abuse). */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/dashboard";
}

type Tab = "sign_in" | "sign_up";
const MIN_PASSWORD = 8;

const inputClass =
  "mt-1.5 h-12 w-full rounded-2xl border border-line-strong bg-canvas px-4 outline-none focus:border-blue";

export function LoginForm() {
  const { mode, status, signInWithEmail, signInWithGoogle, passwordAuth } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [tab, setTab] = useState<Tab>("sign_up");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (status === "signed_in") router.replace(next);
  }, [status, router, next]);

  // Supabase answers "no such account" and "wrong password" with one deliberately vague
  // message, so it cannot be used to discover who has an account. That is right, but handing
  // it to someone straight is our version of page 93 of the manual: the fix is a tab away on
  // this very page and the error never says so.
  const isUnknownLogin = (message: string): boolean => /invalid login credentials/i.test(message);

  const run = async (action: () => Promise<void>): Promise<void> => {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      await action();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign-in failed.";
      setError(
        isUnknownLogin(message)
          ? "That email and password don't match an account. If you haven't made one yet, create an account below — it takes a second."
          : message,
      );
    } finally {
      setBusy(false);
    }
  };

  const onPassword = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    if (password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`);
      return;
    }
    void run(async () => {
      const result = await passwordAuth(tab, email.trim(), password);
      if (result === "check_email") setNotice(`Check ${email} to confirm your account.`);
    });
  };

  const onDev = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void run(async () => {
      await signInWithEmail(email.trim(), next);
    });
  };

  const onMagicLink = (): void => {
    if (!email.trim()) {
      setError("Enter your email first.");
      return;
    }
    void run(async () => {
      await signInWithEmail(email.trim(), next);
      setNotice(`Check ${email} for a sign-in link.`);
    });
  };

  const tabClass = (t: Tab): string =>
    `flex-1 rounded-full py-2 text-sm font-bold transition-colors ${
      tab === t ? "bg-ink text-white" : "text-muted hover:text-ink"
    }`;

  return (
    <div className="blue-grid grid min-h-dvh place-items-center px-4 py-10">
      <div className="animate-pop relative w-full max-w-sm rounded-[1.5rem] border border-line bg-surface p-8 shadow-[var(--shadow-float)]">
        <Logo />
        <h1 className="display-heavy mt-8 text-4xl">Let&apos;s make shorts.</h1>

        {mode === "none" ? (
          <div className="mt-6">
            <Alert tone="error">
              Sign-in isn&apos;t configured. Set the Supabase keys (or enable dev login) — see the
              setup guide in README.md.
            </Alert>
          </div>
        ) : mode === "dev" ? (
          <>
            <div className="mt-6">
              <Alert tone="info">Development login — no password or email is sent.</Alert>
            </div>
            <form onSubmit={onDev} className="mt-4 space-y-3">
              <label className="block">
                <span className="text-sm font-medium">Email</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className={inputClass}
                />
              </label>
              <Button type="submit" className="w-full" size="lg" loading={busy}>
                Continue
              </Button>
            </form>
          </>
        ) : (
          <>
            <div
              role="tablist"
              aria-label="Account"
              className="mt-6 flex rounded-full bg-sunken p-1"
            >
              <button
                type="button"
                role="tab"
                aria-selected={tab === "sign_up"}
                className={tabClass("sign_up")}
                onClick={() => setTab("sign_up")}
              >
                Create account
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={tab === "sign_in"}
                className={tabClass("sign_in")}
                onClick={() => setTab("sign_in")}
              >
                Sign in
              </button>
            </div>

            {env.googleAuth ? (
              <>
                <Button
                  variant="secondary"
                  className="mt-5 w-full"
                  onClick={() =>
                    void signInWithGoogle(next).catch((e: Error) => setError(e.message))
                  }
                >
                  Continue with Google
                </Button>
                <div className="my-4 flex items-center gap-3 text-xs text-muted">
                  <span className="h-px flex-1 bg-line" /> or{" "}
                  <span className="h-px flex-1 bg-line" />
                </div>
              </>
            ) : null}

            <form onSubmit={onPassword} className="mt-4 space-y-3">
              <label className="block">
                <span className="text-sm font-medium">Email</span>
                <input
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className={inputClass}
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium">Password</span>
                <input
                  type="password"
                  required
                  minLength={MIN_PASSWORD}
                  autoComplete={tab === "sign_up" ? "new-password" : "current-password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={tab === "sign_up" ? "At least 8 characters" : "Your password"}
                  className={inputClass}
                />
              </label>
              <Button type="submit" className="w-full uppercase" size="lg" loading={busy}>
                {tab === "sign_up" ? "Create account" : "Sign in"}
              </Button>
            </form>
            <button
              type="button"
              onClick={onMagicLink}
              disabled={busy}
              className="mt-4 inline-flex w-full items-center justify-center gap-1.5 text-xs font-semibold text-muted hover:text-ink"
            >
              <Mail className="size-3.5" aria-hidden /> Email me a sign-in link instead
            </button>
          </>
        )}

        {notice ? (
          <div className="mt-4">
            <Alert tone="success">{notice}</Alert>
          </div>
        ) : null}
        {error ? (
          <div className="mt-4">
            <Alert tone="error">{error}</Alert>
            {tab === "sign_in" && isUnknownLogin(error) ? (
              <button
                type="button"
                onClick={() => {
                  setTab("sign_up");
                  setError(null);
                }}
                className="mt-2 text-sm font-bold text-blue underline underline-offset-2"
              >
                Create an account with this email
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
