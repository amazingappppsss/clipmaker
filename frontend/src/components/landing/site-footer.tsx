/** Closing call-to-action band and footer. */
import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

export function SiteFooter() {
  return (
    <footer className="px-4 py-16 sm:px-6">
      <div className="mesh-gradient mx-auto max-w-6xl rounded-[2.5rem] px-6 py-20 text-center text-white">
        <h2 className="mx-auto max-w-3xl text-4xl font-extrabold tracking-tight sm:text-6xl">
          Your next 10 shorts are already recorded.
        </h2>
        <p className="mx-auto mt-5 max-w-lg text-lg text-white/90">
          They&apos;re hiding in your last long video. Let&apos;s go find them.
        </p>
        <ButtonLink href="/login" variant="white" size="lg" className="mt-9">
          Try it free
        </ButtonLink>
      </div>
      <div className="mx-auto mt-10 flex max-w-6xl flex-col items-center justify-between gap-4 text-sm text-muted sm:flex-row">
        <Logo />
        <p>© ClipMaker. Only upload videos you have the rights to.</p>
      </div>
    </footer>
  );
}
