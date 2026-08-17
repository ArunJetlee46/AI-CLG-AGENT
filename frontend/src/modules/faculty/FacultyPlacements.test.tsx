import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { facultyApi } from "@/modules/faculty/api";
import { FacultyPlacements } from "@/modules/faculty/FacultyPlacements";
import { useAuthStore } from "@/core/stores/auth";

vi.mock("@/modules/faculty/api", () => ({
  facultyApi: {
    placementOverview: vi.fn(),
    schedule: vi.fn(),
    me: vi.fn(),
    overview: vi.fn(),
  },
}));

function renderPlacements() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <FacultyPlacements />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const mockOverview = {
  staff_id: "LEC0001",
  method: "faculty-placement-v1",
  students: [
    { student_id: "23AD001", readiness_score: 85, band: "ready", placement_probability: 0.82, drivers: ["strong GPA 3.5"] },
    { student_id: "23AD005", readiness_score: 55, band: "needs_improvement", placement_probability: 0.45, drivers: ["attendance 72%"] },
    { student_id: "23AD010", readiness_score: 30, band: "not_ready", placement_probability: 0.2, drivers: ["GPA 1.8"] },
  ],
  summary: { total: 3, ready: 1, needs_improvement: 1, not_ready: 1 },
};

describe("FacultyPlacements", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth("test-token", "lecturer", "STAFF001", "refresh-token");
    vi.mocked(facultyApi.placementOverview).mockReset();
  });

  it("renders the page header", async () => {
    vi.mocked(facultyApi.placementOverview).mockResolvedValue(mockOverview);
    renderPlacements();
    expect(screen.getByText("Placement Overview")).toBeInTheDocument();
  });

  it("shows summary badges", async () => {
    vi.mocked(facultyApi.placementOverview).mockResolvedValue(mockOverview);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("3 students")).toBeInTheDocument();
    });
    expect(screen.getByText("1 ready")).toBeInTheDocument();
    expect(screen.getByText("1 needs improvement")).toBeInTheDocument();
    expect(screen.getByText("1 not ready")).toBeInTheDocument();
  });

  it("shows student rows", async () => {
    vi.mocked(facultyApi.placementOverview).mockResolvedValue(mockOverview);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("23AD001")).toBeInTheDocument();
    });
    expect(screen.getByText("23AD005")).toBeInTheDocument();
    expect(screen.getByText("23AD010")).toBeInTheDocument();
  });

  it("shows empty state when no students", async () => {
    vi.mocked(facultyApi.placementOverview).mockResolvedValue({
      ...mockOverview,
      students: [],
      summary: { total: 0, ready: 0, needs_improvement: 0, not_ready: 0 },
    });
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("No placement data")).toBeInTheDocument();
    });
  });
});
