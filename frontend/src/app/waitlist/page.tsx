/**
 * The waitlist at its own address, so referral links already in the wild keep working.
 * Same page as `/`.
 */
import type { Metadata } from "next";

import { WaitlistLanding } from "@/components/waitlist/waitlist-landing";

export const metadata: Metadata = {
  title: "Clip2Easy — founding members",
  description:
    "Join the first 100. We clip your first episode by hand before launch, free, and lock your price at half off for life.",
};

export default function WaitlistPage() {
  return <WaitlistLanding />;
}
