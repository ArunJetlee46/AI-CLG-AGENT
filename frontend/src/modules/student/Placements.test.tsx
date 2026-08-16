import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { studentApi } from "@/modules/student/api";
import { Placements } from "@/modules/student/Placements";
import { useAuthStore } from "@/core/stores/auth";

vi.mock("@/modules/student/api", () => ({
  studentApi: {
    myTimetable: vi.fn(),
    myPlacements: vi.fn(),
    askStudyAssistant: vi.fn(),
  },
}));

const mockPlacements = {
  student_id: "STU001",
  method: "placement-v1",
  readiness: {
    student_id: "STU001",
    readiness_score: 72,
    band: "ready",
    components: [
      { name: "academic", score: 0.8, weight: 0.4 },
      { name: "attendance", score: 0.9, weight: 0.2 },
      { name: "aptitude", score: 0.7, weight: 0.2 },
      { name: "consistency", score: 0.85, weight: 0.2 },
    ],
    placement_probability: 0.75,
    drivers: ["strong academic foundation"],
  },
  shortlists: [
    {
      id: "n1", drive_id: "d1", title: "Shortlisted for Acme Corp", body: "You have been shortlisted.",
      status: "sent", created_at: "2026-06-01T10:00:00",
      drive: { id: "d1", title: "Acme Drive", company: "Acme Corp", drive_date: "2026-07-01", mode: "online", location: "Pune", status: "scheduled" },
    },
  ],
  upcoming_drives: [
    { id: "d1", title: "Acme Drive", company: "Acme Corp", drive_date: "2026-07-01", mode: "online", location: "Pune", status: "scheduled" },
  ],
  note: "Readiness is computed from academic signals plus the ML placement model.",
};

function renderPlacements() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Placements />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Placements", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth("test-token", "student", "student1", "refresh-token");
    vi.mocked(studentApi.myPlacements).mockReset();
  });

  it("renders the page header", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    expect(screen.getByText("My Placements")).toBeInTheDocument();
  });

  it("shows readiness score when loaded", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("72")).toBeInTheDocument();
    });
  });

  it("shows shortlist notification", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("Shortlisted for Acme Corp")).toBeInTheDocument();
    });
  });

  it("shows upcoming drives table", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("Acme Drive")).toBeInTheDocument();
    });
  });
});
