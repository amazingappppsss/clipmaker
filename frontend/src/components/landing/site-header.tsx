"use client";

/** Public site header, drawn on the blue hero panel. */
import Link from "next/link";

import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/lib/auth/auth-provider";

const LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
];

const pill =
  "rounded-full border border-white/70 px-4 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-white hover:text-blue";

export function SiteHeader() {
  const { status } = useAuth();
  return (
    <header className="relative z-20 flex items-center justify-between gap-4 px-5 py-5 sm:px-8">
      <Logo tone="light" />
      <nav className="hidden items-center gap-2 md:flex" aria-label="Main">
        {LINKS.map((l) => (
          <Link key={l.href} href={l.href} className={pill}>
            {l.label}
          </Link>
        ))}
      </nav>
      {status === "signed_in" ? (
        <Link href="/dashboard" className={`${pill} px-6 py-2.5 text-sm`}>
          Dashboard
        </Link>
      ) : (
        <Link href="/login" className={`${pill} px-6 py-2.5 text-sm`}>
          Get started
        </Link>
      )}
    </header>
  );
}
