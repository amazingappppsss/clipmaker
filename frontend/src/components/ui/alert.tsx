/** Inline status message (errors, warnings, confirmations). */
import { AlertCircle, CheckCircle2, Info } from "lucide-react";
import type { ReactNode } from "react";

type Tone = "error" | "success" | "info";

const TONES: Record<Tone, { box: string; Icon: typeof Info }> = {
  error: { box: "bg-danger-soft text-danger", Icon: AlertCircle },
  success: { box: "bg-success-soft text-success", Icon: CheckCircle2 },
  info: { box: "bg-info-soft text-ink-soft", Icon: Info },
};

export function Alert({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  const { box, Icon } = TONES[tone];
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={`flex gap-2.5 rounded-xl px-4 py-3 text-sm ${box}`}
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
