"use client";

/** Public site header. Shows "Dashboard" instead of sign-in buttons when signed in. */
import Link from "next/link";

import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/lib/auth/auth-provider";

export function SiteHeader() {
  const { status } = useAuth();
  return (
    <header className="sticky top-0 z-30 border-b border-transparent bg-canvas/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <nav className="hidden items-center gap-7 text-sm text-ink-soft md:flex" aria-label="Main">
          <Link href="#how-it-works" className="hover:text-ink">
            How it works
          </Link>
          <Link href="#features" className="hover:text-ink">
            Features
          </Link>
          <Link href="#pricing" className="hover:text-ink">
            Pricing
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          {status === "signed_in" ? (
            <ButtonLink href="/dashboard" size="sm">
              Dashboard
            </ButtonLink>
          ) : (
            <>
              <ButtonLink href="/login" variant="ghost" size="sm">
                Log in
              </ButtonLink>
              <ButtonLink href="/login" size="sm">
                Get started
              </ButtonLink>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
