import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Chat } from "@/modules/common/Chat";
import { useAuthStore } from "@/core/stores/auth";

vi.mock("@/core/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/core/lib/api")>();
  return {
    ...actual,
    chatStream: vi.fn(async (_message: string, _token: string, onChunk: (t: string) => void, onDone: (f: object) => void) => {
      onChunk("Hello ");
      onChunk("from the mock.");
      onDone({
        intent: "academic",
        agent: "rag",
        answer: "Hello from the mock.",
        citations: ["CS101"],
        requires_approval: false,
        approval_id: null,
        decision_card_id: null,
        provider: "groq",
        model: "llama",
      });
    }),
  };
});

function renderChat() {
  return render(
    <MemoryRouter>
      <Chat />
    </MemoryRouter>
  );
}

describe("Chat", () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth("test-token", "student", "student1", "refresh-token");
  });

  it("renders the greeting and suggestion chips", () => {
    renderChat();
    expect(screen.getByText(/Beru Campus AI assistant/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Which students are at risk/ })).toBeInTheDocument();
  });

  it("streams a response into the conversation when a suggestion is clicked", async () => {
    renderChat();
    fireEvent.click(screen.getByRole("button", { name: /Which students are at risk/ }));
    await waitFor(() => {
      expect(screen.getByText("Hello from the mock.")).toBeInTheDocument();
    });
    expect(screen.getByText(/intent academic/)).toBeInTheDocument();
  });
});
