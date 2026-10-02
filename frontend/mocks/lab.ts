// Dev fixtures for /api/lab/*: the real eval_results files cut down to the keys the Lab page reads
// (values copied from ladder_table.json, verifier.json, weaklabel_*.json, retrieval.json, asr.json
// as of 3 Oct 2026). Only for development and tests; the real API serves the files themselves.
const c = (nvm: number, lo: number, hi: number, n: number) => ({ n, n_ipos: 7, nvm, nvm_ci95: [lo, hi] });
const f = (nvm: number) => ({ n: 7, nvm });

export const LAB_LADDER = {
  headline_split: "test",
  ladder: {
    rules: {
      label: "Rung 1: rules",
      test: { full: c(0.8571, 0.7857, 0.9286, 56), body_only: c(0.2286, 0.1143, 0.3714, 35) },
    },
    qa_pretrained: {
      label: "Rung 2: pretrained QA",
      test: { full: c(0.3571, 0.2679, 0.4821, 56), body_only: c(0.3714, 0.2286, 0.5143, 35) },
    },
    qa_finetuned: {
      label: "Rung 3: fine-tuned QA",
      test: { full: c(0.7381, 0.6429, 0.8274, 56), body_only: c(0.8476, 0.8, 0.9048, 35) },
    },
  },
  paired_test: {
    qa_finetuned_minus_qa_pretrained: { full: { diff: 0.381, ci95: [0.2262, 0.5238], excludes_zero: true } },
  },
  per_field_test: {
    rules: {
      full: {
        fresh_issue_size: f(1), ofs_shares: f(1), ofs_amount: f(1), total_issue_size: f(1), face_value: f(1),
        book_running_lead_managers: f(0.5714), registrar: f(0.8571), promoters: f(0.5714),
      },
    },
    qa_pretrained: {
      full: {
        fresh_issue_size: f(0.4286), ofs_shares: f(0.2857), ofs_amount: f(0.4286), total_issue_size: f(0.4286),
        face_value: f(0.5714), book_running_lead_managers: f(0.1429), registrar: f(0.2857), promoters: f(0.2857),
      },
    },
    qa_finetuned: {
      full: {
        fresh_issue_size: f(0.8571), ofs_shares: f(0.7143), ofs_amount: f(0.8571), total_issue_size: f(0.8571),
        face_value: f(0.8571), book_running_lead_managers: f(0.5714), registrar: f(0.7143), promoters: f(0.5714),
      },
    },
  },
};

const r = (rate: number, hits: number, n: number) => ({ rate, hits, n, wilson_95: [0, 1] });

export const LAB_VERIFIER = {
  headline: {
    detection: { held_out: r(1, 100, 100), after_one_rule_fix: r(1, 100, 100) },
    scale_mismatch_recall: { held_out: r(0.875, 35, 40), after_one_rule_fix: r(1, 40, 40) },
    false_alarm: { held_out: r(0, 0, 100), after_one_rule_fix: r(0, 0, 100) },
  },
  metrics: {
    detection: r(1, 100, 100),
    false_alarm: r(0, 0, 100),
    per_type: {
      correct: { n: 90, ok: 90 },
      digit: { n: 20, ok: 20 },
      invented: { n: 20, ok: 20 },
      rounding_ok: { n: 10, ok: 10 },
      scale_lakh_crore: { n: 20, ok: 20 },
      scale_million_crore: { n: 20, ok: 20 },
      swap_metric: { n: 20, ok: 20 },
    },
  },
};

export const LAB_WEAKLABELS = {
  n_ipos: 389,
  train: { ipos: 272, examples: 4047, positives: 1624 },
  dev: { ipos: 30, examples: 491, positives: 194 },
  audit: { n: 50, correct: 45, precision: 0.9, wilson_95: [0.7864, 0.9565] },
};

const m = (all: number, hi: number, abstained: string) => ({
  test: { all: { "recall@5": { mean: all } }, hi: { "recall@5": { mean: hi } } },
  abstain: { test_unanswerable_abstained: abstained },
});

export const LAB_RETRIEVAL = {
  methods: {
    bm25: m(0.625, 0.6111, "5/11"),
    dense: m(0.5179, 0.5, "4/11"),
    hybrid: m(0.6429, 0.7222, "0/11"),
    "hybrid+rerank": m(0.6071, 0.5556, "9/11"),
  },
};

export const LAB_ASR = {
  n_clips: 10,
  models: {
    small: { summary: { mean_cer: 0.36 } },
    "large-v3-turbo": { summary: { mean_cer: 0.0617 } },
  },
};
