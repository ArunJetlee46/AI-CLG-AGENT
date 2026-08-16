import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { studentApi } from "@/modules/student/api";
import { Schedule } from "@/modules/student/Schedule";
import { useAuthStore } from "@/core/stores/auth";

vi.mock("@/modules/student/api", () => ({
  studentApi: {
    myTimetable: vi.fn(),
    myPlacements: vi.fn(),
    askStudyAssistant: vi.fn(),
    profile: vi.fn(),
    successScore: vi.fn(),
    alerts: vi.fn(),
    predictions: vi.fn(),
  },
}));

function renderSchedule() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Schedule />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const mockTimetable = {
  student_id: "STU001",
  method: "enrolled-courses-timetable",
  days: ["Monday", "Wednesday"],
  entries: [
    { day: "Monday", term: "2026-S1", start_time: "09:00", end_time: "10:00",
      course_code: "CS101", course_title: "Intro to CS", credits: 3, room: "R101", lecturer: "Dr. Smith" },
    { day: "Wednesday", term: "2026-S1", start_time: "11:00", end_time: "12:00",
      course_code: "CS101", course_title: "Intro to CS", credits: 3, room: "R101", lecturer: "Dr. Smith" },
  ],
  by_day: {
    Monday: [
      { day: "Monday", term: "2026-S1", start_time: "09:00", end_time: "10:00",
        course_code: "CS101", course_title: "Intro to CS", credits: 3, room: "R101", lecturer: "Dr. Smith" },
    ],
    Wednesday: [
      { day: "Wednesday", term: "2026-S1", start_time: "11:00", end_time: "12:00",
        course_code: "CS101", course_title: "Intro to CS", credits: 3, room: "R101", lecturer: "Dr. Smith" },
    ],
  },
};

describe("Schedule", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth("test-token", "student", "student1", "refresh-token");
    vi.mocked(studentApi.myTimetable).mockReset();
  });

  it("renders the page header", async () => {
    vi.mocked(studentApi.myTimetable).mockResolvedValue(mockTimetable);
    renderSchedule();
    expect(screen.getByText("My Schedule")).toBeInTheDocument();
  });

  it("shows timetable entries when loaded", async () => {
    vi.mocked(studentApi.myTimetable).mockResolvedValue(mockTimetable);
    renderSchedule();
    await waitFor(() => {
      expect(screen.getByText("Monday")).toBeInTheDocument();
    });
    expect(screen.getAllByText("CS101").length).toBe(2);
  });

  it("shows empty state when no entries", async () => {
    vi.mocked(studentApi.myTimetable).mockResolvedValue({ ...mockTimetable, days: [], entries: [], by_day: {} });
    renderSchedule();
    await waitFor(() => {
      expect(screen.getByText("No scheduled classes")).toBeInTheDocument();
    });
  });
});
