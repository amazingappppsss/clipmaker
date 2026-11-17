/**
 * The front door. We have not launched, so this is the waitlist — showing a paste bar for a
 * product nobody can use yet would waste the visit.
 *
 * When we open up, swap this back to the product landing that still lives at /product.
 */
import type { Metadata } from "next";

import { WaitlistLanding } from "@/components/waitlist/waitlist-landing";

export const metadata: Metadata = {
  title: "Clip2Easy — your VOD, clipped",
  description:
    "Vertical clips from your stream or episode, found by sound as well as by words. Join the first 100: we cut your first VOD by hand before launch, free, and lock your price at half off for life.",
};

export default function HomePage() {
  return <WaitlistLanding />;
}
