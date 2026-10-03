import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { About } from "./About";
import { HowItWorks } from "./HowItWorks";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

const wrap = (ui: React.ReactNode) => {
  // No backend in unit tests: the risk-level fetch fails, so step 6 shows without a number.
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  return render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);
};

afterEach(() => vi.unstubAllGlobals());

describe("B05 §8 copy", () => {
  it("How it works has the eight upload steps", () => {
    wrap(<HowItWorks />);
    const row = screen.getByRole("region", { name: "Analysing an uploaded document" });
    const steps = within(row).getAllByRole("listitem");
    expect(steps).toHaveLength(8);
    expect(within(steps[5]).getByText("Compare each risk with past IPOs")).toBeInTheDocument();
    expect(within(steps[6]).getByText("Rewrite in plain English and check the numbers")).toBeInTheDocument();
  });

  it("About lists the three new known limits", () => {
    wrap(<About />);
    expect(screen.getByText("Plain-English rewrites can miss nuance; the original is always one click away.")).toBeInTheDocument();
    expect(screen.getByText(/It is not a prediction or a recommendation\.$/)).toBeInTheDocument();
  });
});
