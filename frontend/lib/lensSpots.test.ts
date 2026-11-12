import { describe, expect, it } from "vitest";
import { buildXray } from "@/mocks/xray";
import { LENS_PAGE, lensSpots, spotAt } from "./lensSpots";
import { fieldById, type XField } from "./xray";

const x = buildXray("ather-energy-2025")!;
const on = (id: string, bbox: [number, number, number, number], extra: Partial<XField> = {}): XField => ({
  ...fieldById(x.fields, id)!,
  doc: "rhp",
  page: LENS_PAGE.page,
  bbox,
  ...extra,
});

describe("lensSpots", () => {
  it("keeps only boxed facts on the lens page, top to bottom, as page shares", () => {
    const fields = [
      on("face_value", [432.6, 161.3, 485.6, 168.5]),
      on("total_issue_size", [102, 100, 187, 107]),
      { ...fieldById(x.fields, "registrar")!, page: 9 },
      on("ofs_shares", [10, 10, 20, 20], { bbox: null }),
    ];
    const spots = lensSpots(fields, "per share");
    expect(spots.map((s) => s.id)).toEqual(["total_issue_size", "face_value"]);
    expect(spots[1].x).toBeCloseTo(432.6 / LENS_PAGE.width);
    expect(spots[1].h).toBeCloseTo(7.2 / LENS_PAGE.height);
  });

  it("shows a blank [●] with the value the final prospectus filled in", () => {
    const blank = fieldById(x.fields, "offer_price")!;
    const [s] = lensSpots([on("offer_price", [75, 153, 90, 160], { value: blank.value })], "per share");
    expect(s.value).toBe("[●]");
    expect(s.mark).toBe("placeholder");
    expect(s.filled).toBeTruthy();
  });
});

describe("spotAt", () => {
  const spots = lensSpots([on("face_value", [432.6, 161.3, 485.6, 168.5])], "per share");
  it("finds the spot under the lens and nothing far away", () => {
    expect(spotAt(spots, 0.77, 0.195, 0.08)?.id).toBe("face_value");
    expect(spotAt(spots, 0.2, 0.8, 0.08)).toBeNull();
  });
});
