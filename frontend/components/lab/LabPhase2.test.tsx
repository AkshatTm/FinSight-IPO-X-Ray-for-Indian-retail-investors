import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LabChecks, LabClassifier, LabNovelty, LabSegmentation } from "./LabPhase2";
import { LabRewrites, LabRiskLevelCheck, LabSpeedCost } from "./LabPhase2More";

// Synthetic payloads in the B06 §5 shapes, for rendering only (no real result has been run).
const RISKLEVEL = {
  outcomes: [
    {
      key: "listing_day_return",
      rho: -0.12,
      ci95: [-0.25, 0.02],
      n: 210,
      by_level: [
        { level: "Low", n: 70, p25: -0.02, median: 0.11, p75: 0.3 },
        { level: "High", n: 70, p25: -0.08, median: 0.06, p75: 0.22 },
      ],
    },
  ],
};

describe("Phase 2 Lab sections", () => {
  it("render nothing when the result files are missing", () => {
    const { container } = render(
      <>
        <LabSegmentation data={undefined} />
        <LabChecks summary={undefined} redflags={undefined} />
        <LabClassifier data={undefined} />
        <LabRewrites simplify={undefined} readability={undefined} />
        <LabNovelty data={undefined} />
        <LabRiskLevelCheck data={undefined} />
        <LabSpeedCost latency={undefined} cost={undefined} />
      </>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("show the E21 verdict even when there is no clear relationship", () => {
    render(<LabRiskLevelCheck data={RISKLEVEL} />);
    expect(screen.getByRole("heading", { name: "Does the risk level match what happened?" })).toBeInTheDocument();
    expect(screen.getByText("There is no clear relationship between the risk level and the listing-day return.")).toBeInTheDocument();
    expect(screen.getByText(/Spearman ρ -0.12 \(95% range -0.25 to 0.02\), 210 IPOs\./)).toBeInTheDocument();
    expect(screen.getByText("+11.0%")).toBeInTheDocument();
  });

  it("show the spec headings, the honesty line and unknown reason keys as written", () => {
    render(
      <>
        <LabSegmentation data={{ precision: 0.9, recall: 0.8, f1: 0.85, n_docs: 12 }} />
        <LabChecks summary={{ nvm: 0.82, n: 300 }} redflags={{ accuracy: 0.9, n: 130, labels: ["OK", "Watch"], confusion: [[50, 5], [8, 67]] }} />
        <LabClassifier data={{ systems: [{ file: "classifier_tfidf", model: "tfidf-logreg", gold: { macro_f1: 0.48, n: 150 } }] }} />
        <LabRewrites simplify={{ checks: { n: 200, rejected: 20, reasons: { numbers: 12, odd_reason: 8 } } }} readability={undefined} />
        <LabNovelty data={{ chosen_tau: 0.8, points: [{ tau: 0.8, precision: 0.75, n: 20 }] }} />
        <LabSpeedCost latency={{ stages: [{ stage: "parsed", p50_s: 41.2, p95_s: 80 }], n_docs: 8 }} cost={{ inr_per_upload_mean: 1.5, inr_per_upload_max: 3.25, free_share: 0.012 }} />
      </>,
    );
    for (const h of ["Splitting risks", "Reading the financial checks", "Sorting risks into categories", "Plain-English rewrites", "Unusualness", "Speed and cost"])
      expect(screen.getByRole("heading", { name: h })).toBeInTheDocument();
    expect(screen.getByText("How often FinSight separates the risks correctly.")).toBeInTheDocument();
    expect(screen.getByText("The rewrites are checked for numbers and certainty, not for every shade of meaning.")).toBeInTheDocument();
    expect(screen.getByText("a number changed or added", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("odd_reason", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("0.80 (used)")).toBeInTheDocument();
    expect(screen.getByText("₹1.5")).toBeInTheDocument();
    expect(screen.getByText("1.2%")).toBeInTheDocument();
  });
});
