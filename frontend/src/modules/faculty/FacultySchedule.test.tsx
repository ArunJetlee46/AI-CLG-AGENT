import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { facultyApi } from "@/modules/faculty/api";
import { FacultySchedule } from "@/modules/faculty/FacultySchedule";
import { useAuthStore } from "@/core/stores/auth";

vi.mock("@/modules/faculty/api", () => ({
  facultyApi: {
    schedule: vi.fn(),
    placementOverview: vi.fn(),
    me: vi.fn(),
    overview: vi.fn(),
  },
}));

function renderSchedule() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <FacultySchedule />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const mockSchedule = {
  staff_id: "LEC0001",
  total_hours: 12,
  max_hours: 18,
  utilization: 66.7,
  overloaded: false,
  sessions: 6,
  days: [
    {
      day: "MON",
      slots: [
        { course_code: "CS201", title: "Database Systems", start: "09:00", end: "10:30", hours: 1.5 },
        { course_code: "CS301", title: "Operating Systems", start: "14:00", end: "15:00", hours: 1.0 },
      ],
    },
    {
      day: "WED",
      slots: [
        { course_code: "CS201", title: "Database Systems", start: "09:00", end: "10:30", hours: 1.5 },
      ],
    },
  ],
  advisory: "Load is within the weekly cap.",
};

describe("FacultySchedule", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth("test-token", "lecturer", "STAFF001", "refresh-token");
    vi.mocked(facultyApi.schedule).mockReset();
  });

  it("renders the page header", async () => {
    vi.mocked(facultyApi.schedule).mockResolvedValue(mockSchedule);
    renderSchedule();
    expect(screen.getByText("My Schedule")).toBeInTheDocument();
  });

  it("shows schedule days and sessions", async () => {
    vi.mocked(facultyApi.schedule).mockResolvedValue(mockSchedule);
    renderSchedule();
    await waitFor(() => {
      expect(screen.getByText("MON")).toBeInTheDocument();
    });
    expect(screen.getAllByText("CS201").length).toBe(2);
    expect(screen.getByText("WED")).toBeInTheDocument();
  });

  it("shows empty state when no days", async () => {
    vi.mocked(facultyApi.schedule).mockResolvedValue({ ...mockSchedule, days: [] });
    renderSchedule();
    await waitFor(() => {
      expect(screen.getByText("No scheduled classes")).toBeInTheDocument();
    });
  });
});
