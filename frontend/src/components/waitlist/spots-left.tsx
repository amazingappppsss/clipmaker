"use client";

/**
 * Real scarcity or none at all: this reads the live count from the API and renders nothing
 * if the call fails. A made-up "only 3 left!" is the fastest way to lose someone who checks.
 */
import { useEffect, useState } from "react";

import type { WaitlistStats } from "@/services/api-types";
import { getWaitlistStats } from "@/services/waitlist";

export function SpotsLeft() {
  const [stats, setStats] = useState<WaitlistStats | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    getWaitlistStats()
      .then((value) => {
        if (!abort.signal.aborted) setStats(value);
      })
      .catch(() => setStats(null)); // silence is better than a fake number
    return () => abort.abort();
  }, []);

  if (!stats) return null;

  const taken = Math.min(stats.total, stats.founding_spots);
  const pct = Math.round((taken / stats.founding_spots) * 100);

  return (
    <div className="mx-auto mt-8 max-w-sm">
      <div className="flex items-end justify-between text-sm font-semibold text-white">
        <span>
          {stats.spots_left > 0 ? (
            <>
              <span className="font-display text-lg font-black text-lime">{stats.spots_left}</span>{" "}
              founding spots left
            </>
          ) : (
            <>Founding spots are gone — join for the launch list</>
          )}
        </span>
        <span className="text-white/70">
          {taken}/{stats.founding_spots}
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/25">
        <div
          className="h-full rounded-full bg-lime transition-[width] duration-700"
          style={{ width: `${Math.max(2, pct)}%` }}
        />
      </div>
    </div>
  );
}
