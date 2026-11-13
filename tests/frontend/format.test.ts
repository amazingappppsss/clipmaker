import { describe, expect, it } from "vitest";

import {
  formatBytes,
  formatDate,
  formatDuration,
  formatInr,
} from "@/lib/format";

describe("formatBytes", () => {
  it.each([
    [0, "0 B"],
    [1536, "1.5 KB"],
    [87_539_813, "83.5 MB"],
    [5 * 1024 ** 3, "5.0 GB"],
    [-1, "—"],
  ])("%d → %s", (input, expected) => expect(formatBytes(input)).toBe(expected));
});

describe("formatDuration", () => {
  it.each([
    [45, "0:45"],
    [65, "1:05"],
    [3725, "1:02:05"],
    [null, "—"],
  ])("%s → %s", (input, expected) =>
    expect(formatDuration(input)).toBe(expected),
  );
});

describe("formatDate / formatInr", () => {
  it("formats ISO dates", () =>
    expect(formatDate("2026-11-13T10:00:00Z")).toBe("13 Nov 2026"));
  it("handles invalid dates", () => expect(formatDate("nope")).toBe("—"));
  it("formats rupees", () => {
    expect(formatInr(0)).toBe("Free");
    expect(formatInr(1999)).toBe("₹1,999");
  });
});
