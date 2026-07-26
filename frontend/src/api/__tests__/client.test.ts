import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setAuthTokenGetter } from "../auth_token";
import { get, post } from "../client";

function mockFetchOnce(body: unknown, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api client auth header", () => {
  beforeEach(() => {
    setAuthTokenGetter(async () => null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("does not attach an Authorization header when unauthenticated", async () => {
    const fetchMock = mockFetchOnce({ ok: true });
    await get("/api/whatever");
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBeUndefined();
  });

  it("attaches the Bearer token on GET when authenticated", async () => {
    setAuthTokenGetter(async () => "abc123");
    const fetchMock = mockFetchOnce({ ok: true });
    await get("/api/whatever");
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer abc123");
  });

  it("attaches the Bearer token on POST when authenticated", async () => {
    setAuthTokenGetter(async () => "abc123");
    const fetchMock = mockFetchOnce({ ok: true });
    await post("/api/whatever", { foo: "bar" });
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer abc123");
  });
});
