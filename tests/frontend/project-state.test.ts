import { describe, expect, it } from "vitest";

import {
  PIPELINE_STEPS,
  isProcessing,
  stateTone,
  stepStatuses,
  stepStatusesFromJob,
} from "@/lib/project-state";

describe("stepStatuses", () => {
  it("marks nothing done before processing starts", () => {
    expect(stepStatuses("UPLOADED").every((s) => s === "pending")).toBe(true);
  });

  it("marks earlier stages done and the current one active", () => {
    const statuses = stepStatuses("SELECTING");
    expect(statuses.slice(0, 3)).toEqual(["done", "done", "done"]);
    expect(statuses[3]).toBe("current");
    expect(statuses.slice(4).every((s) => s === "pending")).toBe(true);
  });

  it("never claims progress for a failed project", () => {
    expect(stepStatuses("FAILED").every((s) => s === "pending")).toBe(true);
  });

  it("marks all done when completed", () => {
    expect(stepStatuses("COMPLETED")).toEqual(PIPELINE_STEPS.map(() => "done"));
  });
});

describe("tones and polling", () => {
  it("polls only while working", () => {
    expect(isProcessing("RENDERING")).toBe(true);
    expect(isProcessing("UPLOADED")).toBe(false);
    expect(isProcessing("COMPLETED")).toBe(false);
  });
  it("maps terminal tones", () => {
    expect(stateTone("FAILED")).toBe("danger");
    expect(stateTone("NEEDS_REVIEW")).toBe("warning");
  });
});

describe("stepStatusesFromJob", () => {
  it("maps real backend stage records, including failures", () => {
    const stages = PIPELINE_STEPS.map((s, i) => ({
      stage: s.state,
      status: (["done", "done", "failed"][i] ?? "pending") as
        | "done"
        | "failed"
        | "pending",
      attempts: 1,
    }));
    expect(stepStatusesFromJob(stages).slice(0, 4)).toEqual([
      "done",
      "done",
      "failed",
      "pending",
    ]);
  });

  it("shows running as current", () => {
    const stages = [
      {
        stage: "TRANSCRIBING" as const,
        status: "running" as const,
        attempts: 1,
      },
    ];
    expect(stepStatusesFromJob(stages)[1]).toBe("current");
  });
});
