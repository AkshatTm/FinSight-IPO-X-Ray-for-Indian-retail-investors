// Measured values copied from eval_results/final/FINAL_SCORECARD.md (re-measured 3 Nov 2026,
// pipeline_version 4.2, single run, gold v3 over all 10 showcase IPOs). Never edit by hand: update
// the scorecard and copy the number here.
export const SCORECARD = {
  /** E14 summary extraction, numeric value match, 195 valued rows (e14_today.json). */
  factsNvm: 0.774,
  factsRows: 195,
  /** E15 red-flag status accuracy, 13 checks x 10 IPOs = 130 statuses (e15_today.json). */
  redflagStatus: 0.769,
  redflagStatuses: 130,
} as const;
