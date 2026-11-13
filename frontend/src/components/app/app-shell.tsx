"use client";

/**
 * Layout for signed-in pages: auth guard + top navigation with credits.
 * Signed-out visitors are redirected to /login?next=<current path>.
 */
import { LogOut, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/lib/auth/auth-provider";
import { getUsage } from "@/services/account";

const NAV = [
  { href: "/dashboard", label: "Projects" },
  { href: "/account", label: "Account" },
];

function CreditsPill() {
  const [credits, setCredits] = useState<number | null>(null);
  const pathname = usePathname();
  useEffect(() => {
    getUsage()
      .then((u) => setCredits(u.credits_balance))
      .catch(() => setCredits(null));
  }, [pathname]);
  if (credits === null) return null;
  return (
    <Link
      href="/account"
      className="hidden items-center rounded-full bg-violet/15 px-3.5 py-1.5 text-sm font-semibold text-violet-bright ring-1 ring-violet/30 hover:bg-violet/25 sm:inline-flex"
      title="1 credit = 1 minute of video"
    >
      <span className="font-extrabold tabular-nums">{credits}</span>&nbsp;credits
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { status, user, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "signed_out") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [status, router, pathname]);

  if (status !== "signed_in") {
    return (
      <div className="grid min-h-dvh place-items-center text-muted">
        <Spinner />
      </div>
    );
  }

  return (
    <div className="relative min-h-dvh">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-80 bg-gradient-to-b from-violet/12 to-transparent"
      />
      <header className="sticky top-0 z-30 border-b border-line bg-canvas/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4 sm:px-6">
          <Logo href="/dashboard" />
          <nav className="flex items-center gap-1 text-sm" aria-label="App">
            {NAV.map((item) => {
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-full px-4 py-2 font-semibold ${active ? "bg-sunken text-ink" : "text-muted hover:bg-sunken hover:text-ink"}`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <CreditsPill />
            <ButtonLink href="/new" size="sm">
              <Plus className="size-4" aria-hidden />
              <span className="hidden sm:inline">New project</span>
            </ButtonLink>
            <button
              type="button"
              onClick={() => void signOut().then(() => router.push("/"))}
              className="grid size-9 place-items-center rounded-full text-muted hover:bg-sunken hover:text-ink"
              aria-label={`Sign out${user?.email ? ` (${user.email})` : ""}`}
              title={user?.email ?? "Sign out"}
            >
              <LogOut className="size-4" />
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">{children}</main>
    </div>
  );
}
