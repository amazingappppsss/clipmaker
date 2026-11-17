"use client";

/**
 * The waitlist form, and what someone sees once they're on it.
 *
 * Two things worth knowing:
 * - `company` is a honeypot. It's hidden from people and ignored by the backend, which answers
 *   a filled-in one exactly like a real signup so bots get no feedback.
 * - A `?ref=` code in the URL is passed through so the referrer gets credit. It's a public
 *   code, not a secret, and the backend refuses to let anyone credit themselves.
 */
import { ArrowRight, Check, Copy, Loader2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { ApiError } from "@/services/api-client";
import type { WaitlistPlace } from "@/services/api-types";
import { joinWaitlist } from "@/services/waitlist";

function shareUrl(code: string): string {
  if (typeof window === "undefined") return "";
  return `${window.location.origin}/waitlist?ref=${encodeURIComponent(code)}`;
}

function Joined({ place }: { place: WaitlistPlace }) {
  const [copied, setCopied] = useState(false);
  const link = shareUrl(place.referral_code);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="animate-pop rounded-[1.75rem] bg-white p-6 text-ink sm:p-8">
      <p className="text-xs font-bold tracking-widest text-blue uppercase">You&rsquo;re in</p>
      <p className="display-heavy mt-2 text-4xl sm:text-5xl">
        #{place.position}
        <span className="ml-2 align-middle text-base font-semibold text-muted">
          of {place.total}
        </span>
      </p>
      <p className="mt-3 text-sm text-muted">
        Check your inbox when we open the doors. Want your free episode sooner?
      </p>

      <p className="display-heavy mt-6 text-lg">
        Every friend who joins moves you up {place.places_per_referral} places.
      </p>
      {place.referrals > 0 ? (
        <p className="mt-1 text-sm font-semibold text-blue">
          {place.referrals} {place.referrals === 1 ? "person has" : "people have"} joined on your
          link so far.
        </p>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded-full bg-sunken px-4 py-2.5 text-sm">
          {link}
        </code>
        <button
          type="button"
          onClick={copy}
          className="inline-flex items-center gap-2 rounded-full bg-ink px-5 py-2.5 font-display text-sm font-black text-white uppercase transition-transform hover:scale-105"
        >
          {copied ? (
            <Check className="size-4" aria-hidden />
          ) : (
            <Copy className="size-4" aria-hidden />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}

export function WaitlistForm({ source = "waitlist" }: { source?: string }) {
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState(""); // honeypot
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [place, setPlace] = useState<WaitlistPlace | null>(null);

  if (place) return <Joined place={place} />;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const ref = params.get("ref");
      setPlace(
        await joinWaitlist({
          email: email.trim(),
          source,
          company,
          ...(ref ? { referral_code: ref } : {}),
        }),
      );
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Something went wrong. Please try again in a moment.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} noValidate>
      <div className="flex flex-col gap-2 rounded-[1.5rem] border border-line-strong bg-white p-2 shadow-card sm:flex-row sm:rounded-full">
        <label className="sr-only" htmlFor="waitlist-email">
          Email address
        </label>
        <input
          id="waitlist-email"
          type="email"
          required
          autoComplete="email"
          inputMode="email"
          maxLength={320}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@yourshow.com"
          className="min-w-0 flex-1 rounded-full bg-transparent px-5 py-3 text-ink outline-none placeholder:text-muted"
        />
        {/* Honeypot: off-screen, not announced, never autofilled. */}
        <input
          type="text"
          name="company"
          tabIndex={-1}
          autoComplete="off"
          aria-hidden="true"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          className="pointer-events-none absolute left-[-9999px] size-0 opacity-0"
        />
        <button
          type="submit"
          disabled={busy}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-lime px-7 py-3 font-display font-black text-ink uppercase transition-transform hover:scale-105 disabled:opacity-70"
        >
          {busy ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <ArrowRight className="size-4" aria-hidden />
          )}
          {busy ? "Saving" : "Claim my spot"}
        </button>
      </div>
      {error ? (
        <div className="mt-4">
          <Alert tone="error">{error}</Alert>
        </div>
      ) : null}
    </form>
  );
}
