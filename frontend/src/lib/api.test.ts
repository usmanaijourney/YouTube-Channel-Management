import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api";

describe("api client error handling", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on a successful response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [{ channel_id: "channel-001" }],
      })
    );

    const result = await api.channels();
    expect(result).toEqual([{ channel_id: "channel-001" }]);
  });

  it("throws ApiError with the backend's detail message on a non-OK response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({ detail: "channel 'x' not found" }),
      })
    );

    await expect(api.channelDetail("x")).rejects.toMatchObject({
      status: 404,
      message: "channel 'x' not found",
    });
  });

  it("throws a network ApiError when fetch itself rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("failed to fetch"))
    );

    await expect(api.systemHealth()).rejects.toBeInstanceOf(ApiError);
    await expect(api.systemHealth()).rejects.toMatchObject({ status: 0 });
  });

  it("omits undefined query params rather than sending them as 'undefined'", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);

    await api.alerts(undefined);

    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).not.toContain("severity");
  });
});
