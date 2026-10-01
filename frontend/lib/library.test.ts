import { describe, expect, it } from "vitest";
import { IPOS } from "@/mocks/fixtures";
import { filterSortIpos, isPureOfs, splitPct } from "./library";

describe("library filtering and sorting", () => {
  it("sorts newest first with missing dates last", () => {
    const l = filterSortIpos([...IPOS, { ...IPOS[0], id: "x", company: "X", listing_date: null }], {
      query: "",
      sort: "newest",
      filter: "all",
    });
    expect(l[0].listing_date! >= l[1].listing_date!).toBe(true);
    expect(l[l.length - 1].id).toBe("x");
  });
  it("sorts largest issue first and A to Z", () => {
    const big = filterSortIpos(IPOS, { query: "", sort: "largest", filter: "all" });
    expect(big[0].id).toBe("tata-capital-2025");
    const az = filterSortIpos(IPOS, { query: "", sort: "az", filter: "all" });
    expect(az[0].company.startsWith("Ather")).toBe(true);
  });
  it("searches company and sector, case-insensitively", () => {
    expect(filterSortIpos(IPOS, { query: "LENS", sort: "az", filter: "all" }).map((i) => i.id)).toEqual(["lenskart-2025"]);
    expect(filterSortIpos(IPOS, { query: "education", sort: "az", filter: "all" })).toHaveLength(1);
    expect(filterSortIpos(IPOS, { query: "zzz", sort: "az", filter: "all" })).toHaveLength(0);
  });
  it("filters fresh issue and pure offer for sale", () => {
    const ofs = filterSortIpos(IPOS, { query: "", sort: "az", filter: "ofs" });
    expect(ofs.every(isPureOfs)).toBe(true);
    expect(ofs.map((i) => i.id)).toContain("lg-electronics-india-2025");
    const fresh = filterSortIpos(IPOS, { query: "", sort: "az", filter: "fresh" });
    expect(fresh.map((i) => i.id)).not.toContain("lg-electronics-india-2025");
  });
  it("splits fresh and OFS shares", () => {
    const s = splitPct({ ...IPOS[0], issue_size_inr: "100", fresh_inr: "64", ofs_inr: "36" })!;
    expect(s.fresh).toBe(64);
    expect(s.ofs).toBe(36);
    expect(splitPct({ ...IPOS[0], issue_size_inr: null, fresh_inr: null, ofs_inr: null })).toBeNull();
    expect(splitPct({ ...IPOS[0], fresh_inr: null, ofs_inr: "50", issue_size_inr: "50" })!.fresh).toBe(0);
  });
});
