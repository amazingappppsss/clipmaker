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
    <section id="pricing" className="scroll-mt-8 px-4 pb-24 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <h2 className="display-heavy text-center text-4xl sm:text-6xl">
          Start free. <span className="text-blue">Go pro later.</span>
        </h2>
        <p className="mt-4 text-center text-muted">1 credit = 1 minute of uploaded video.</p>

        {plans === null ? (
          <div className="mt-12 flex justify-center text-muted">
            {failed ? (
              <p className="rounded-full bg-surface px-5 py-2.5 text-sm font-medium">
                Pricing is unavailable right now.
              </p>
            ) : (
              <Spinner />
            )}
          </div>
        ) : (
          <div className="mt-12 grid items-stretch gap-4 md:grid-cols-3">
            {plans.map((plan) => {
              const hi = plan.plan === HIGHLIGHT;
              return (
                <div
                  key={plan.plan}
                  className={`flex flex-col rounded-[1.75rem] p-8 ${hi ? "blue-grid text-white" : "bg-surface"}`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="display-heavy text-xl">{plan.name}</h3>
                    {hi ? (
                      <span className="rounded-full bg-lime px-3 py-1 text-xs font-bold text-ink">
                        Most popular
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-6 flex items-baseline gap-1">
                    <span className="display-heavy text-5xl">{formatInr(plan.price_inr)}</span>
                    {plan.price_inr > 0 ? (
                      <span className={hi ? "text-white/75" : "text-muted"}>/mo</span>
                    ) : null}
                  </p>
                  <ul className="mt-7 flex-1 space-y-3 text-sm">
                    {features(plan).map((f) => (
                      <li key={f} className="flex gap-2.5">
                        <span
                          className={`grid size-5 shrink-0 place-items-center rounded-full ${hi ? "bg-lime text-ink" : "bg-blue text-white"}`}
                        >
                          <Check className="size-3" aria-hidden />
                        </span>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <ButtonLink
                    href="/login"
                    variant={hi ? "lime" : "dark"}
                    size="lg"
                    className="mt-8 w-full uppercase"
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
