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
    <section id="pricing" className="scroll-mt-20 px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <h2 className="text-center text-3xl font-semibold tracking-tight sm:text-4xl">
          Simple pricing
        </h2>
        <p className="mt-4 text-center text-muted">
          1 credit = 1 minute of uploaded video. Start free.
        </p>

        {plans === null ? (
          <div className="mt-12 flex justify-center text-muted">
            {failed ? <p className="text-sm">Pricing is unavailable right now.</p> : <Spinner />}
          </div>
        ) : (
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {plans.map((plan) => {
              const highlighted = plan.plan === HIGHLIGHT;
              return (
                <div
                  key={plan.plan}
                  className={`flex flex-col rounded-[var(--radius-card)] border p-7 ${
                    highlighted
                      ? "border-ink bg-ink text-white shadow-[var(--shadow-float)]"
                      : "border-line bg-surface"
                  }`}
                >
                  <h3 className="font-semibold">{plan.name}</h3>
                  <p className="mt-4 flex items-baseline gap-1">
                    <span className="text-4xl font-semibold tracking-tight">
                      {formatInr(plan.price_inr)}
                    </span>
                    {plan.price_inr > 0 ? (
                      <span className={highlighted ? "text-white/60" : "text-muted"}>/month</span>
                    ) : null}
                  </p>
                  <ul className="mt-6 flex-1 space-y-2.5 text-sm">
                    {features(plan).map((f) => (
                      <li key={f} className="flex gap-2">
                        <Check
                          className={`mt-0.5 size-4 shrink-0 ${highlighted ? "text-coral" : "text-success"}`}
                          aria-hidden
                        />
                        {f}
                      </li>
                    ))}
                  </ul>
                  <ButtonLink
                    href="/login"
                    variant={highlighted ? "secondary" : "primary"}
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
