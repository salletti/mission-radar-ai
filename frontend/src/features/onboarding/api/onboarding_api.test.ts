import { afterEach, describe, expect, it, vi } from "vitest";
import { uploadCv } from "./onboarding_api";

const mockDraftResponse = {
  cv_profile: {
    email: "john@example.com",
    full_name: "John Doe",
    title: "Senior Developer",
    years_experience: 10,
    preferred_contract_type: "freelance",
    target_tjm: 700,
    preferred_remote_mode: "full_remote",
    location: "Paris",
    skills: ["React", "TypeScript"],
    availability: "2025-06-01T00:00:00",
  },
  cv_raw_text: "John Doe — Senior Developer...",
};

describe("uploadCv", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns parsed response on success", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDraftResponse),
    } as Response);

    const file = new File(["content"], "cv.pdf", { type: "application/pdf" });
    const result = await uploadCv("john@example.com", file);

    expect(result).toEqual(mockDraftResponse);

    const [url, options] = (
      global.fetch as ReturnType<typeof vi.fn>
    ).mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/onboarding/cv");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
  });

  it("throws error with detail message on API failure", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: () =>
        Promise.resolve({ detail: "Only PDF files are accepted" }),
    } as Response);

    const file = new File(["content"], "cv.txt", { type: "text/plain" });
    await expect(uploadCv("john@example.com", file)).rejects.toThrow(
      "Only PDF files are accepted"
    );
  });

  it("throws status-based error when response body is not JSON", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: () => Promise.reject(new Error("not json")),
    } as unknown as Response);

    const file = new File(["content"], "cv.pdf", { type: "application/pdf" });
    await expect(uploadCv("john@example.com", file)).rejects.toThrow(
      "Erreur 502"
    );
  });
});
