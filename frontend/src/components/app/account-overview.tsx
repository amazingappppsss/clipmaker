"use client";

/** Account page: plan, credits and usage history (PRD §6-F). */
import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { formatDate, formatUsd } from "@/lib/format";
import { getUsage } from "@/services/account";
import { ApiError } from "@/services/api-client";
import type { AccountUsage } from "@/services/api-types";

export function AccountOverview() {
  const [usage, setUsage] = useState<AccountUsage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch((err: unknown) =>
        setError(err instanceof ApiError ? err.message : "Couldn't load your account."),
      );
  }, []);

  if (error) return <Alert tone="error">{error}</Alert>;
  if (!usage)
    return (
      <div className="flex justify-center py-20 text-muted">
        <Spinner />
      </div>
    );

  const plan = usage.plans.find((p) => p.plan === usage.plan);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="display-heavy text-4xl">Account</h1>
        <p className="mt-1 text-muted">{usage.email ?? "Signed in"}</p>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6">
          <p className="text-sm text-muted">Credits remaining</p>
          <p className="mt-2 display-heavy text-5xl tabular-nums">{usage.credits_balance}</p>
          <p className="mt-1 text-sm text-muted">1 credit = 1 minute of uploaded video</p>
        </div>
        <div className="rounded-[var(--radius-card)] border border-line bg-surface p-6">
          <p className="text-sm text-muted">Current plan</p>
          <p className="mt-2 display-heavy text-5xl">{plan?.name ?? usage.plan}</p>
          <p className="mt-1 text-sm text-muted">
            {plan
              ? `${plan.monthly_credits} credits / month · ${formatUsd(plan.price_usd_cents)}`
              : ""}
            {" · "}Paid plans launch soon
          </p>
        </div>
      </div>

      <section>
        <h2 className="text-lg font-semibold">Usage history</h2>
        <div className="mt-3 overflow-hidden rounded-[var(--radius-card)] border border-line bg-surface">
          {usage.history.length === 0 ? (
            <p className="p-6 text-sm text-muted">No activity yet.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-sunken text-left text-xs text-muted">
                <tr>
                  <th className="px-5 py-2.5 font-medium">Date</th>
                  <th className="px-5 py-2.5 font-medium">Description</th>
                  <th className="px-5 py-2.5 text-right font-medium">Credits</th>
                </tr>
              </thead>
              <tbody>
                {usage.history.map((r) => (
                  <tr key={r.id} className="border-t border-line">
                    <td className="px-5 py-3 whitespace-nowrap text-muted">
                      {formatDate(r.created_at)}
                    </td>
                    <td className="px-5 py-3">{r.description}</td>
                    <td
                      className={`px-5 py-3 text-right font-medium tabular-nums ${r.credits > 0 ? "text-success" : ""}`}
                    >
                      {r.credits > 0 ? `+${r.credits}` : r.credits}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
