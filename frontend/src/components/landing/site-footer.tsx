/** Closing call-to-action and footer. */
import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

export function SiteFooter() {
  return (
    <footer className="border-t border-line px-4 pt-24 pb-10 sm:px-6">
      <div className="spotlight mx-auto max-w-6xl overflow-hidden rounded-[1.75rem] border border-line bg-surface px-6 py-20 text-center">
        <h2 className="mx-auto max-w-2xl text-4xl font-bold tracking-tight sm:text-5xl">
          Your next 10 shorts are already recorded.
        </h2>
        <p className="mx-auto mt-4 max-w-md text-muted">
          They&apos;re hiding in your last long video. Let&apos;s go find them.
        </p>
        <ButtonLink href="/login" size="lg" className="mt-8">
          Get clips free
        </ButtonLink>
      </div>
      <div className="mx-auto mt-10 flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-muted sm:flex-row">
        <Logo />
        <p>© ClipMaker. Only upload videos you have the rights to.</p>
      </div>
    </footer>
  );
}
