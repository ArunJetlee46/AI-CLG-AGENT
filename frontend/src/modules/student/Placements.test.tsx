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
    applyToDrive: vi.fn(),
    withdrawApplication: vi.fn(),
    decideOffer: vi.fn(),
    uploadResume: vi.fn(),
    getResume: vi.fn(),
    deleteResume: vi.fn(),
    askStudyAssistant: vi.fn(),
  },
}));

const mockPlacements = {
  student_id: "STU001",
  method: "placement-v2",
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
  open_drives: [
    { id: "d1", title: "Acme Drive", company: "Acme Corp", drive_date: "2026-07-01", mode: "online", location: "Pune", status: "scheduled", applied: false, notified: true },
  ],
  applications: [
    { id: "a1", drive_id: "d2", status: "applied", applied_at: "2026-06-10T10:00:00",
      drive: { id: "d2", title: "TechCorp Drive", company: "TechCorp", drive_date: "2026-08-01", mode: "onsite", location: "Chennai", status: "scheduled" } },
  ],
  offers: [
    { id: "o1", drive_id: "d3", round_reached: "final", offered_ctc: 8.5, offer_status: "offered", decided_at: null, created_at: "2026-07-01T10:00:00",
      drive: { id: "d3", title: "MegaCorp Drive", company: "MegaCorp", drive_date: "2026-06-15", mode: "onsite", location: "Bangalore", status: "completed" } },
  ],
  resume: { id: "r1", filename: "john_doe.pdf", skills: ["python", "javascript"], uploaded_at: "2026-05-01T10:00:00" },
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

  it("shows open drives with apply button", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
      expect(screen.getByText("Apply")).toBeInTheDocument();
    });
  });

  it("shows applications with status", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("TechCorp")).toBeInTheDocument();
    });
  });

  it("shows offers with accept/reject buttons", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("MegaCorp")).toBeInTheDocument();
      expect(screen.getByText("Accept")).toBeInTheDocument();
      expect(screen.getByText("Reject")).toBeInTheDocument();
    });
  });

  it("shows resume info", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("john_doe.pdf")).toBeInTheDocument();
    });
  });

  it("shows shortlist notification", async () => {
    vi.mocked(studentApi.myPlacements).mockResolvedValue(mockPlacements);
    renderPlacements();
    await waitFor(() => {
      expect(screen.getByText("Shortlisted for Acme Corp")).toBeInTheDocument();
    });
  });
});
