import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, setTokenGetter } from "@/services/api-client";

function mockFetch(status: number, body: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(body === undefined ? null : JSON.stringify(body), {
          status,
        }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
  setTokenGetter(async () => null);
});

describe("apiRequest", () => {
  it("refuses authenticated calls without a token", async () => {
    await expect(apiRequest("/projects")).rejects.toMatchObject({
      code: "unauthorized",
    });
  });

  it("sends the bearer token and parses JSON", async () => {
    setTokenGetter(async () => "tok");
    mockFetch(200, { ok: 1 });
    await expect(apiRequest("/projects")).resolves.toEqual({ ok: 1 });
    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect((init?.headers as Record<string, string>).Authorization).toBe(
      "Bearer tok",
    );
  });

  it("maps backend errors to ApiError with the stable code", async () => {
    setTokenGetter(async () => "tok");
    mockFetch(422, { code: "no_audio", message: "No audio track." });
    const err = await apiRequest("/x").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 422,
      code: "no_audio",
      message: "No audio track.",
    });
  });

  it("reports network failures clearly", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Promise.reject(new TypeError("fail"))),
    );
    await expect(
      apiRequest("/plans", { anonymous: true }),
    ).rejects.toMatchObject({ code: "network_error" });
  });
});
