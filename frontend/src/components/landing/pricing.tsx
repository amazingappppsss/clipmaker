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

function PlanCard({ plan }: { plan: PlanInfo }) {
  const highlighted = plan.plan === HIGHLIGHT;
  const card = (
    <div className="flex h-full flex-col rounded-[calc(2rem-3px)] bg-surface p-8">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-extrabold">{plan.name}</h3>
        {highlighted ? (
          <span className="gradient-fill rounded-full px-3 py-1 text-xs font-bold text-white">
            Most popular
          </span>
        ) : null}
      </div>
      <p className="mt-5 flex items-baseline gap-1">
        <span className="font-display text-5xl font-extrabold tracking-tight">
          {formatInr(plan.price_inr)}
        </span>
        {plan.price_inr > 0 ? <span className="text-muted">/month</span> : null}
      </p>
      <ul className="mt-7 flex-1 space-y-3 text-sm">
        {features(plan).map((f) => (
          <li key={f} className="flex gap-2.5">
            <span className="grid size-5 shrink-0 place-items-center rounded-full bg-success-soft text-success">
              <Check className="size-3" aria-hidden />
            </span>
            {f}
          </li>
        ))}
      </ul>
      <ButtonLink href="/login" variant={highlighted ? "primary" : "dark"} className="mt-8 w-full">
        {plan.price_inr === 0 ? "Start free" : `Choose ${plan.name}`}
      </ButtonLink>
    </div>
  );
  return highlighted ? (
    <div className="rounded-[2rem] bg-gradient-to-br from-magenta via-coral to-violet p-[3px] shadow-[var(--shadow-glow)] md:-translate-y-3">
      {card}
    </div>
  ) : (
    <div className="rounded-[2rem] p-[3px] ring-1 ring-line">{card}</div>
  );
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
    <section id="pricing" className="scroll-mt-8 bg-sunken px-4 py-24 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <p className="text-center text-sm font-bold tracking-widest text-coral uppercase">
          Pricing
        </p>
        <h2 className="mt-3 text-center text-4xl font-extrabold tracking-tight sm:text-6xl">
          Start free. <span className="gradient-text">Scale when you&apos;re hooked.</span>
        </h2>
        <p className="mt-5 text-center text-lg text-muted">
          1 credit = 1 minute of uploaded video.
        </p>

        {plans === null ? (
          <div className="mt-14 flex justify-center text-muted">
            {failed ? (
              <p className="rounded-full bg-surface px-5 py-2.5 text-sm font-medium ring-1 ring-line">
                Pricing is unavailable right now.
              </p>
            ) : (
              <Spinner />
            )}
          </div>
        ) : (
          <div className="mt-14 grid items-stretch gap-5 md:grid-cols-3">
            {plans.map((plan) => (
              <PlanCard key={plan.plan} plan={plan} />
            ))}
          </div>
        )}
        <p className="mt-8 text-center text-xs text-muted">
          Prices in INR. Paid plans launch soon — everyone starts on the free trial.
        </p>
      </div>
    </section>
  );
}
