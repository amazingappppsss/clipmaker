import { describe, expect, it } from "vitest";

import { resolveContentType, titleFromFilename } from "@/services/upload";

const file = (name: string, type = ""): File => new File(["x"], name, { type });

describe("resolveContentType", () => {
  it("trusts known browser types", () =>
    expect(resolveContentType(file("a.mp4", "video/mp4"))).toBe("video/mp4"));
  it("infers from extension when type is empty", () => {
    expect(resolveContentType(file("a.MKV"))).toBe("video/x-matroska");
    expect(resolveContentType(file("a.mov"))).toBe("video/quicktime");
    expect(resolveContentType(file("a.m4v"))).toBe("video/mp4");
  });
  it("rejects unsupported files", () => {
    expect(resolveContentType(file("a.avi", "video/x-msvideo"))).toBeNull();
    expect(resolveContentType(file("notes.txt", "text/plain"))).toBeNull();
  });
});

describe("titleFromFilename", () => {
  it("cleans separators and extension", () =>
    expect(titleFromFilename("my_podcast-ep-12.mp4")).toBe("my podcast ep 12"));
  it("falls back for empty names", () =>
    expect(titleFromFilename(".mp4")).toBe("Untitled video"));
});
