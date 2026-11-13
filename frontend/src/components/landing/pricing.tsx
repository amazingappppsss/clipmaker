"use client";

/** Pricing section, loaded from the backend's public GET /plans (single source of truth). */
import { Check } from "lucide-react";
import { useEffect, useState } from "react";

import { ButtonLink } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { formatInr } from "@/lib/format";
import { listPlans } from "@/services/account";
import type { PlanInfo } from "@/services/api-types";

const HIGHLIGHT: PlanInfo["plan"] = "creator";

function features(plan: PlanInfo): string[] {
  return [
    `${plan.monthly_credits} minutes of video / month`,
    plan.watermark ? "ClipMaker watermark" : "No watermark",
    "Captions, titles & hashtags",
    "Automatic quality checks",
  ];
}

export function Pricing() {
  const [plans, setPlans] = useState<PlanInfo[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    listPlans()
      .then(setPlans)
      .catch(() => setFailed(true));
  }, []);

  return (
    <section id="pricing" className="scroll-mt-8 border-t border-line px-4 py-24 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <p className="text-center text-sm font-medium text-violet-bright">Pricing</p>
        <h2 className="mt-3 text-center text-4xl font-bold tracking-tight sm:text-5xl">
          Start free. Upgrade when it clicks.
        </h2>
        <p className="mt-4 text-center text-muted">1 credit = 1 minute of uploaded video.</p>

        {plans === null ? (
          <div className="mt-12 flex justify-center text-muted">
            {failed ? (
              <p className="rounded-full border border-line px-4 py-2 text-sm">
                Pricing is unavailable right now.
              </p>
            ) : (
              <Spinner />
            )}
          </div>
        ) : (
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {plans.map((plan) => {
              const highlighted = plan.plan === HIGHLIGHT;
              return (
                <div
                  key={plan.plan}
                  className={`flex flex-col rounded-[var(--radius-card)] border bg-surface p-7 ${
                    highlighted ? "border-violet/70 shadow-[var(--shadow-glow)]" : "border-line"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="font-semibold">{plan.name}</h3>
                    {highlighted ? (
                      <span className="rounded-full bg-violet/15 px-2.5 py-1 text-xs font-medium text-violet-bright ring-1 ring-violet/30">
                        Most popular
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-5 flex items-baseline gap-1">
                    <span className="font-display text-4xl font-bold tracking-tight">
                      {formatInr(plan.price_inr)}
                    </span>
                    {plan.price_inr > 0 ? <span className="text-sm text-muted">/month</span> : null}
                  </p>
                  <ul className="mt-6 flex-1 space-y-3 text-sm text-ink-soft">
                    {features(plan).map((f) => (
                      <li key={f} className="flex gap-2.5">
                        <Check className="mt-0.5 size-4 shrink-0 text-violet-bright" aria-hidden />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <ButtonLink
                    href="/login"
                    variant={highlighted ? "primary" : "secondary"}
                    className="mt-8 w-full"
                  >
                    {plan.price_inr === 0 ? "Start free" : `Choose ${plan.name}`}
                  </ButtonLink>
                </div>
              );
            })}
          </div>
        )}
        <p className="mt-6 text-center text-xs text-muted">
          Prices in INR. Paid plans launch soon — everyone starts on the free trial.
        </p>
      </div>
    </section>
  );
}
