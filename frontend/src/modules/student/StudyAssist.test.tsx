import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { studentApi } from "@/modules/student/api";
import { StudyAssist } from "@/modules/student/StudyAssist";
import { useAuthStore } from "@/core/stores/auth";

vi.mock("@/modules/student/api", () => ({
  studentApi: {
    myTimetable: vi.fn(),
    myPlacements: vi.fn(),
    askStudyAssistant: vi.fn(),
  },
}));

const mockAnswer = {
  student_id: "STU001",
  answer: "The OS syllabus covers process scheduling, memory management, and file systems.",
  sources: [
    { document: "os.pdf", page_start: 1, page_end: 5, course_code: "CS301", course_title: "Operating Systems",
      regulation: "R2020", programme: "B.Tech", score: 0.92 },
  ],
  retrieved: [],
  grounded: true,
};

function renderStudyAssist() {
  return render(
    <MemoryRouter>
      <StudyAssist />
    </MemoryRouter>
  );
}

describe("StudyAssist", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth("test-token", "student", "student1", "refresh-token");
    vi.mocked(studentApi.askStudyAssistant).mockReset();
  });

  it("renders the greeting and suggestion chips", () => {
    renderStudyAssist();
    expect(screen.getByText(/curriculum study assistant/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /What is covered in the OS syllabus/ })).toBeInTheDocument();
  });

  it("streams an answer when a suggestion is clicked", async () => {
    vi.mocked(studentApi.askStudyAssistant).mockResolvedValue(mockAnswer);
    renderStudyAssist();
    fireEvent.click(screen.getByRole("button", { name: /What is covered in the OS syllabus/ }));
    await waitFor(() => {
      expect(screen.getByText(/process scheduling/)).toBeInTheDocument();
    });
    expect(screen.getByText(/CS301/)).toBeInTheDocument();
  });

  it("shows error state on failure", async () => {
    vi.mocked(studentApi.askStudyAssistant).mockRejectedValue(new Error("network error"));
    renderStudyAssist();
    fireEvent.click(screen.getByRole("button", { name: /What is covered in the OS syllabus/ }));
    await waitFor(() => {
      expect(screen.getByText(/Error: network error/)).toBeInTheDocument();
    });
  });
});
