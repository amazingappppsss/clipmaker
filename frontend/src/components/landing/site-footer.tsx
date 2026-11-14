/** Closing call-to-action panel and footer. */
import { SpinBadge } from "@/components/landing/spin-badge";
import { Squiggle } from "@/components/landing/squiggle";
import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

export function SiteFooter() {
  return (
    <footer className="px-2 pb-8 sm:px-4">
      <div className="blue-grid relative overflow-hidden rounded-[2rem] px-6 py-20 text-center text-white sm:rounded-[2.75rem] sm:py-28">
        <Squiggle className="absolute top-10 left-[8%] hidden w-24 text-lime sm:block" />
        <SpinBadge className="absolute right-[6%] bottom-8 hidden md:grid" />
        <h2 className="display-heavy mx-auto max-w-4xl text-4xl sm:text-7xl">
          Your next 10 shorts are <span className="text-lime">already recorded</span>
        </h2>
        <p className="mx-auto mt-6 max-w-md text-white/85">
          They&apos;re hiding in your last long video. Let&apos;s go find them.
        </p>
        <ButtonLink href="/login" variant="lime" size="lg" className="mt-10 uppercase">
          Get clips free
        </ButtonLink>
      </div>
      <div className="mx-auto mt-8 flex max-w-6xl flex-col items-center justify-between gap-4 px-4 text-sm text-muted sm:flex-row">
        <Logo />
        <p>© Clip2Easy. Only upload videos you have the rights to.</p>
      </div>
    </footer>
  );
}
