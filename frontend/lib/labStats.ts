// Landing stats from the Model Lab payloads (spec 5.9). Each returns null when the value is missing,
// and the stat is then hidden. Shapes: evaluate/seeded_errors.py (`detection.rate`) and
// evaluate/ladder.py (`ladder.qa_finetuned.<split>.body_only.nvm`).

type Json = Record<string, unknown>;
const isObj = (v: unknown): v is Json => typeof v === "object" && v !== null && !Array.isArray(v);

function find(node: unknown, key: string, depth = 0): unknown {
  if (!isObj(node) || depth > 4) return undefined;
  if (key in node) return node[key];
  for (const v of Object.values(node)) {
    const hit = find(v, key, depth + 1);
    if (hit !== undefined) return hit;
  }
  return undefined;
}

const pct = (x: unknown): number | null =>
  typeof x === "number" && Number.isFinite(x) && x >= 0 && x <= 1 ? Math.round(x * 100) : null;

export function detectionPct(verifier: unknown): number | null {
  // `metrics.detection` is the overall rate; `headline.detection` splits held-out and after-fix.
  const metrics = isObj(verifier) ? verifier.metrics : undefined;
  const d = isObj(metrics) && "detection" in metrics ? metrics.detection : find(verifier, "detection");
  return isObj(d) ? pct(d.rate) : pct(d);
}

export function robustPct(ladder: unknown): number | null {
  const l = isObj(ladder) ? ladder.ladder : undefined;
  const split = isObj(ladder) && typeof ladder.headline_split === "string" ? ladder.headline_split : "test";
  const rung = isObj(l) ? l.qa_finetuned : undefined;
  const row = isObj(rung) ? rung[split] : undefined;
  const body = isObj(row) ? row.body_only : undefined;
  return isObj(body) ? pct(body.nvm) : null;
}
