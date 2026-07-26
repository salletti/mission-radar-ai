import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { type ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CvUploadForm from "./cv_upload_form";
import * as api from "../api/onboarding_api";

vi.mock("../api/onboarding_api");

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>
  );
}

const mockProps = {
  onAnalyzeStart: vi.fn(),
  onAnalyzeSuccess: vi.fn(),
  onAnalyzeError: vi.fn(),
};

const mockDraft = {
  cv_profile: {
    email: "john@example.com",
    full_name: "John Doe",
    title: "Senior Developer",
    years_experience: 10,
    preferred_contract_type: "freelance",
    target_tjm: 700,
    preferred_remote_mode: "full_remote",
    location: null,
    skills: ["React", "TypeScript"],
    availability: "2025-06-01T00:00:00",
  },
  cv_raw_text: "raw text",
};

describe("CvUploadForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows email validation error for invalid email", async () => {
    const user = userEvent.setup();
    renderWithClient(<CvUploadForm {...mockProps} />);

    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.click(screen.getByText("Analyze CV"));

    await waitFor(() => {
      expect(screen.getByText("Valid email required")).toBeInTheDocument();
    });
  });

  it("shows file validation error when no file is selected", async () => {
    const user = userEvent.setup();
    renderWithClient(<CvUploadForm {...mockProps} />);

    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.click(screen.getByText("Analyze CV"));

    await waitFor(() => {
      expect(screen.getByText("PDF file required")).toBeInTheDocument();
    });
  });

  it("calls onAnalyzeStart then onAnalyzeSuccess on valid upload", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockResolvedValue(mockDraft);

    renderWithClient(<CvUploadForm {...mockProps} />);

    const file = new File(["pdf content"], "cv.pdf", {
      type: "application/pdf",
    });
    await user.type(screen.getByLabelText("Email"), "john@example.com");
    await user.upload(screen.getByLabelText("CV (PDF)"), file);
    await user.click(screen.getByText("Analyze CV"));

    await waitFor(() => {
      expect(mockProps.onAnalyzeStart).toHaveBeenCalledOnce();
      expect(mockProps.onAnalyzeSuccess).toHaveBeenCalledWith(mockDraft);
    });
  });

  it("calls onAnalyzeError when API returns an error", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockRejectedValue(
      new Error("LLM service unavailable")
    );

    renderWithClient(<CvUploadForm {...mockProps} />);

    const file = new File(["pdf content"], "cv.pdf", {
      type: "application/pdf",
    });
    await user.type(screen.getByLabelText("Email"), "john@example.com");
    await user.upload(screen.getByLabelText("CV (PDF)"), file);
    await user.click(screen.getByText("Analyze CV"));

    await waitFor(() => {
      expect(mockProps.onAnalyzeError).toHaveBeenCalledWith(
        "LLM service unavailable"
      );
    });
  });

  it("disables the button while uploading", async () => {
    const user = userEvent.setup();
    vi.mocked(api.uploadCv).mockImplementation(
      () => new Promise(() => {})
    );

    renderWithClient(<CvUploadForm {...mockProps} />);

    const file = new File(["pdf content"], "cv.pdf", {
      type: "application/pdf",
    });
    await user.type(screen.getByLabelText("Email"), "john@example.com");
    await user.upload(screen.getByLabelText("CV (PDF)"), file);
    await user.click(screen.getByText("Analyze CV"));

    await waitFor(() => {
      expect(screen.getByText("Analyzing...")).toBeDisabled();
    });
  });
});
