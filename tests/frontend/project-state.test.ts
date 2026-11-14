import { describe, expect, it } from "vitest";

import {
  LIVE_STEPS,
  PIPELINE_STEPS,
  currentLiveStep,
  elapsedLabel,
  stepCopy,
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

describe("live processing helpers", () => {
  it("only counts the stages that actually run", () => {
    expect(LIVE_STEPS.map((s) => s.state)).toEqual([
      "INGESTING",
      "TRANSCRIBING",
      "UNDERSTANDING",
      "SELECTING",
      "EDITING",
      "RENDERING",
      "QUALITY_CHECK",
    ]);
  });

  it("finds the running stage from real statuses", () => {
    expect(currentLiveStep(["done", "current", "pending", "pending"])).toBe(1);
    expect(currentLiveStep(["done", "done", "pending", "pending"])).toBe(2);
    expect(currentLiveStep(["done", "done", "done", "done"])).toBe(-1);
  });

  it("formats elapsed time", () => {
    const start = "2026-01-01T00:00:00Z";
    expect(elapsedLabel(start, Date.parse(start) + 75_000)).toBe("1:15");
    expect(elapsedLabel(start, Date.parse(start) + 3_725_000)).toBe("1:02:05");
    expect(elapsedLabel(null, 0)).toBe("");
  });

  it("describes link downloads differently from uploads", () => {
    expect(stepCopy("INGESTING", true).title).toBe("Fetching your video");
    expect(stepCopy("INGESTING", false).title).toBe("Preparing your video");
  });
});
