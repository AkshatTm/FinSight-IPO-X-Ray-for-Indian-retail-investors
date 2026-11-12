import type { MarkState } from "@/components/facts/VerdictMark";
import { scalarText, type XField } from "@/lib/xray";

/** The landing lens page: page 3 of the Ather Energy RHP, in PDF points (see public/landing). */
export const LENS_PAGE = { ipo: "ather-energy-2025", doc: "rhp" as const, page: 3, width: 595.44, height: 841.68 };

/** A fact the hero lens can find: where it sits on the page (0-1 shares) and what FinSight read. */
export interface Spot {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  value: string;
  mark: MarkState;
  /** Set when the RHP prints `[●]`: the value the final prospectus filled in, if any. */
  filled: string | null;
}

/** Facts with a stored box on the lens page, in reading order (top to bottom, left to right). */
export function lensSpots(fields: XField[], perShare: string): Spot[] {
  const out: Spot[] = [];
  for (const f of fields) {
    if (f.doc !== LENS_PAGE.doc || f.page !== LENS_PAGE.page || !f.bbox || !f.value) continue;
    const [x0, y0, x1, y1] = f.bbox;
    const placeholder = f.value.kind === "placeholder";
    const companion = f.companion?.value && f.companion.value.kind !== "placeholder" ? f.companion.value : null;
    const value = placeholder ? "[●]" : scalarText(f.field_id, f.value, "crore", perShare);
    if (!value) continue;
    out.push({
      id: f.field_id,
      x: x0 / LENS_PAGE.width,
      y: y0 / LENS_PAGE.height,
      w: (x1 - x0) / LENS_PAGE.width,
      h: (y1 - y0) / LENS_PAGE.height,
      value,
      mark: placeholder ? "placeholder" : f.verdict,
      filled: placeholder && companion ? scalarText(f.field_id, companion, "crore", perShare) : null,
    });
  }
  return out.sort((a, b) => a.y - b.y || a.x - b.x);
}

/** The spot under the lens centre (page shares), if its centre is within `reach` of it. */
export function spotAt(spots: Spot[], x: number, y: number, reach: number): Spot | null {
  let best: Spot | null = null;
  let bestD = reach;
  for (const s of spots) {
    const d = Math.hypot(s.x + s.w / 2 - x, (s.y + s.h / 2 - y) * (LENS_PAGE.height / LENS_PAGE.width));
    if (d < bestD) {
      best = s;
      bestD = d;
    }
  }
  return best;
}
