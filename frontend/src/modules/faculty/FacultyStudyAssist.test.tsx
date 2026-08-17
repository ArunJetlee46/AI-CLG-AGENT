import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { facultyApi } from "@/modules/faculty/api";
import { FacultyStudyAssist } from "@/modules/faculty/FacultyStudyAssist";
import { useAuthStore } from "@/core/stores/auth";

vi.mock("@/modules/faculty/api", () => ({
  facultyApi: {
    askStudyAssistant: vi.fn(),
    schedule: vi.fn(),
    placementOverview: vi.fn(),
  },
}));

function renderStudy() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <FacultyStudyAssist />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("FacultyStudyAssist", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth("test-token", "lecturer", "STAFF001", "refresh-token");
    vi.mocked(facultyApi.askStudyAssistant).mockReset();
  });

  it("renders the greeting and suggestion chips", () => {
    renderStudy();
    expect(screen.getByText(/curriculum study assistant/i)).toBeInTheDocument();
    expect(screen.getByText("What is covered in the OS syllabus?")).toBeInTheDocument();
  });

  it("streams an answer when a suggestion is clicked", async () => {
    vi.mocked(facultyApi.askStudyAssistant).mockResolvedValue({
      staff_id: "LEC0001",
      answer: "OS covers process scheduling, memory management, and file systems.",
      sources: [{ document: "os_syllabus.pdf", page_start: 1, course_code: "CS301", score: 0.9 }],
      retrieved: [],
      grounded: true,
    });
    renderStudy();
    const chip = screen.getByText("What is covered in the OS syllabus?");
    fireEvent.click(chip);
    await waitFor(() => {
      expect(screen.getByText(/process scheduling/)).toBeInTheDocument();
    });
  });

  it("shows error state on failure", async () => {
    vi.mocked(facultyApi.askStudyAssistant).mockRejectedValue(new Error("unavailable"));
    renderStudy();
    const chip = screen.getByText("What is covered in the OS syllabus?");
    fireEvent.click(chip);
    await waitFor(() => {
      expect(screen.getByText(/Error: unavailable/)).toBeInTheDocument();
    });
  });
});
