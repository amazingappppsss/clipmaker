"use client";

/** Public site header (dark theme). */
import Link from "next/link";

import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/lib/auth/auth-provider";

const LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
];

export function SiteHeader() {
  const { status } = useAuth();
  return (
    <header className="relative z-20 border-b border-line/60">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="hidden items-center gap-8 text-sm text-muted md:flex" aria-label="Main">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="transition-colors hover:text-ink">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {status === "signed_in" ? (
            <ButtonLink href="/dashboard" variant="dark" size="sm">
              Dashboard
            </ButtonLink>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden px-3 py-2 text-sm font-medium text-muted hover:text-ink sm:inline-flex"
              >
                Log in
              </Link>
              <ButtonLink href="/login" variant="dark" size="sm">
                Get started
              </ButtonLink>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
