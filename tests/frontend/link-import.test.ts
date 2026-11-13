import { describe, expect, it } from "vitest";

import {
  hasPendingUpload,
  setPendingLink,
  setPendingUpload,
  takePendingLink,
  takePendingUpload,
} from "@/lib/pending-upload";
import { looksLikeYouTubeUrl } from "@/lib/youtube";

describe("looksLikeYouTubeUrl", () => {
  it.each([
    "https://www.youtube.com/watch?v=abc",
    "youtu.be/abc",
    "https://youtube.com/shorts/xyz",
    "  https://m.youtube.com/watch?v=1  ",
  ])("accepts %s", (url) => expect(looksLikeYouTubeUrl(url)).toBe(true));

  it.each([
    "",
    "hello",
    "http://youtube.com/watch?v=a",
    "https://vimeo.com/1",
    "https://youtube.com.evil.com",
  ])("rejects %s", (url) => expect(looksLikeYouTubeUrl(url)).toBe(false));
});

describe("landing → /new hand-off", () => {
  it("keeps a pasted link once (survives reloads via localStorage)", () => {
    setPendingLink("https://youtu.be/abc");
    expect(takePendingLink()).toBe("https://youtu.be/abc");
    expect(takePendingLink()).toBeNull();
  });

  it("peeks a pending file without consuming it", () => {
    setPendingUpload(new File(["x"], "a.mp4", { type: "video/mp4" }));
    expect(hasPendingUpload()).toBe(true);
    expect(takePendingUpload()?.name).toBe("a.mp4");
    expect(hasPendingUpload()).toBe(false);
  });
});
