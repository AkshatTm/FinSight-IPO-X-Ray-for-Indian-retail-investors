import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { RiskLevel } from "@/lib/report";
import { RiskLevelCard } from "./RiskLevelCard";

const LEVEL = {
  level: "high",
  points: 12,
  max_points: 24,
  score: 0.5,
  percentile: 81.6,
  checks_available: 10,
  reasons: [{ source: "redflag", id: "RF04", label: "Who gets the IPO money", points: 2, link: "#redflag-RF04" }],
  thresholds: { low_below: 0.2, high_from: 0.4 },
  corpus_n: 312,
  provisional: false,
  behind_click: false,
  disclaimer_key: "risklevel.disclaimer",
} as RiskLevel;

const DISCLAIMER = /It is not a recommendation to apply, buy or avoid/;

describe("RiskLevelCard", () => {
  it("shows the level, the percentile line, reasons and the fixed disclaimer", async () => {
    const onReason = vi.fn();
    render(<RiskLevelCard level={LEVEL} onReason={onReason} />);
    expect(screen.getByRole("heading", { name: "Risk level: High" })).toBeInTheDocument();
    expect(screen.getByText("More disclosed risk than 82% of 312 past Indian IPOs.")).toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /close/i })).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Who gets the IPO money · +2"));
    expect(onReason).toHaveBeenCalledWith("#redflag-RF04");
  });
  it("behind a click: level hidden, disclaimer visible before and after", async () => {
    render(<RiskLevelCard level={{ ...LEVEL, behind_click: true }} onReason={() => {}} />);
    expect(screen.queryByText("Risk level: High")).not.toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Show the risk level" }));
    expect(screen.getByText("Risk level: High")).toBeInTheDocument();
    expect(screen.getByText(DISCLAIMER)).toBeInTheDocument();
  });
  it("provisional thresholds: no corpus line, a provisional note; the modal explains the points", async () => {
    render(<RiskLevelCard level={{ ...LEVEL, corpus_n: 0, provisional: true }} onReason={() => {}} />);
    expect(screen.queryByText(/past Indian IPOs\.$/)).not.toBeInTheDocument();
    expect(screen.getByText(/Provisional/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "How the risk level works" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Each Concern adds 2 points and each Watch adds 1.");
  });
});
