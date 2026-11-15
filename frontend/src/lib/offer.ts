/**
 * The founding-member offer, in one place.
 *
 * These are promises to real people, so every line here has to be one we will actually keep.
 * `FOUNDING_SPOTS` must match `FOUNDING_SPOTS` in backend/src/clipmaker/services/waitlist.py.
 */
export const FOUNDING_SPOTS = 100;

export interface OfferItem {
  kicker: string;
  title: string;
  body: string;
  worth: string;
}

export const OFFER: OfferItem[] = [
  {
    kicker: "Before launch",
    title: "We clip your first episode by hand",
    body: "Send one link after you join. We run it ourselves, check every cut, and email you the shorts. No account, no card, nothing to install.",
    worth: "What an editor charges: $20–50 a clip",
  },
  {
    kicker: "Forever",
    title: "Founding price, locked for life",
    body: "Half off whatever the public price ends up being, for as long as you keep your account — including every feature we add later.",
    worth: "50% off, permanently",
  },
  {
    kicker: "At launch",
    title: "100 free minutes, not 15",
    body: "Everyone else starts with 15 minutes of video. Founding members start with 100, so you can run a couple of full episodes before you ever think about paying.",
    worth: "6× the free tier",
  },
  {
    kicker: "Your say",
    title: "You help build it",
    body: "Founding members get a direct line to us. Tell us what your clips need and it goes to the top of the list — that's the whole reason we're doing this before launch.",
    worth: "Shape the product",
  },
];

/** What we will and won't do with an address — stated plainly on the page. */
export const PROMISES: string[] = [
  "One email when your spot opens. No drip sequence, no newsletter.",
  "We never sell or share your address, and we don't run ads on it.",
  "Unsubscribe in one click, and we delete your row if you ask.",
];
