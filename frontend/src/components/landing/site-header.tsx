"use client";

/** Public site header, drawn on top of the gradient hero (white text). */
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
    <header className="relative z-20">
      <div className="mx-auto flex h-20 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo tone="light" />
        <nav
          className="hidden items-center gap-1 rounded-full bg-white/15 p-1 text-sm font-medium text-white backdrop-blur md:flex"
          aria-label="Main"
        >
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className="rounded-full px-4 py-2 hover:bg-white/20">
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {status === "signed_in" ? (
            <ButtonLink href="/dashboard" variant="white" size="sm">
              Dashboard
            </ButtonLink>
          ) : (
            <>
              <Link
                href="/login"
                className="hidden rounded-full px-4 py-2 text-sm font-semibold text-white hover:bg-white/15 sm:inline-flex"
              >
                Log in
              </Link>
              <ButtonLink href="/login" variant="white" size="sm">
                Get started
              </ButtonLink>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
