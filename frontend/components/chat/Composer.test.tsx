import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Composer } from "./Composer";

describe("Composer", () => {
  it("sends on Enter, adds a line on Shift+Enter, ignores empty text", async () => {
    const onSend = vi.fn();
    render(<Composer disabled={false} onSend={onSend} />);
    const box = screen.getByPlaceholderText("Ask a question");
    await userEvent.type(box, "Who are the promoters?{Enter}");
    expect(onSend).toHaveBeenCalledWith("Who are the promoters?");
    expect(box).toHaveValue("");
    await userEvent.type(box, "a{Shift>}{Enter}{/Shift}b");
    expect(box).toHaveValue("a\nb");
    expect(onSend).toHaveBeenCalledTimes(1);
    await userEvent.clear(box);
    await userEvent.type(box, "   {Enter}");
    expect(onSend).toHaveBeenCalledTimes(1);
  });
  it("does not send while an answer is streaming", async () => {
    const onSend = vi.fn();
    render(<Composer disabled onSend={onSend} />);
    await userEvent.type(screen.getByPlaceholderText("Ask a question"), "hello{Enter}");
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });
  it("shows the counter after 250 characters and stops at 300", async () => {
    render(<Composer disabled={false} onSend={() => {}} />);
    const box = screen.getByPlaceholderText("Ask a question");
    expect(screen.queryByText(/of 300/)).toBeNull();
    await userEvent.click(box);
    await userEvent.paste("x".repeat(260));
    expect(screen.getByText("260 of 300")).toBeInTheDocument();
    await userEvent.paste("y".repeat(100));
    expect((box as HTMLTextAreaElement).value.length).toBe(300);
  });
  it("focuses the box when / is pressed outside a field", async () => {
    render(<Composer disabled={false} onSend={() => {}} />);
    await userEvent.keyboard("/");
    expect(screen.getByPlaceholderText("Ask a question")).toHaveFocus();
  });
});
