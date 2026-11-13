/** Closing call-to-action and footer. */
import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

export function SiteFooter() {
  return (
    <footer className="px-4 pb-10 sm:px-6">
      <div className="relative mx-auto max-w-5xl overflow-hidden rounded-[1.75rem] bg-ink px-6 py-16 text-center text-white">
        <div
          aria-hidden
          className="brand-glow absolute -bottom-24 left-1/2 h-48 w-[60%] -translate-x-1/2 opacity-70"
        />
        <h2 className="relative text-3xl font-semibold tracking-tight sm:text-4xl">
          Your next 10 shorts are{" "}
          <span className="font-display font-normal italic">already recorded.</span>
        </h2>
        <ButtonLink href="/login" variant="secondary" size="lg" className="relative mt-8">
          Try it free
        </ButtonLink>
      </div>
      <div className="mx-auto mt-10 flex max-w-5xl flex-col items-center justify-between gap-4 text-sm text-muted sm:flex-row">
        <Logo />
        <p>© ClipMaker. Only upload videos you have the rights to.</p>
      </div>
    </footer>
  );
}
