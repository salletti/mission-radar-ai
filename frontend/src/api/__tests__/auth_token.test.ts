import { beforeEach, describe, expect, it } from "vitest";
import { getAuthToken, setAuthTokenGetter } from "../auth_token";

describe("auth_token bridge", () => {
  beforeEach(() => {
    setAuthTokenGetter(async () => null);
  });

  it("returns null when no getter has been set", async () => {
    expect(await getAuthToken()).toBeNull();
  });

  it("returns whatever the registered getter resolves to", async () => {
    setAuthTokenGetter(async () => "test-token");
    expect(await getAuthToken()).toBe("test-token");
  });

  it("reflects the latest getter after being reset", async () => {
    setAuthTokenGetter(async () => "first-token");
    setAuthTokenGetter(async () => "second-token");
    expect(await getAuthToken()).toBe("second-token");
  });
});
