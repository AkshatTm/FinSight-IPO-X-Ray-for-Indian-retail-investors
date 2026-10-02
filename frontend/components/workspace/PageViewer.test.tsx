import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HighlightBox, pageUrl } from "./PageViewer";

describe("HighlightBox", () => {
  const h = { ipoId: "x", doc: "rhp" as const, page: 3, bbox: [72, 410, 301, 423] as [number, number, number, number], kind: "source" as const, nonce: 1 };
  it("positions the box as a percentage of the page so zoom never moves it", () => {
    render(<HighlightBox h={h} pageW={600} pageH={800} />);
    const el = screen.getByTestId("highlight");
    expect(el.style.left).toBe("12%");
    expect(parseFloat(el.style.top)).toBeCloseTo(51.25);
    expect(parseFloat(el.style.width)).toBeCloseTo(38.1667, 3);
  });
  it("uses the stamp colour for sources and the verdict colour for evidence", () => {
    const { rerender } = render(<HighlightBox h={h} pageW={600} pageH={800} />);
    expect(screen.getByTestId("highlight").style.outline).toContain("--stamp");
    rerender(<HighlightBox h={{ ...h, kind: "contradicted" }} pageW={600} pageH={800} />);
    expect(screen.getByTestId("highlight").style.outline).toContain("--bad");
  });
  it("builds page URLs with the document", () => {
    expect(pageUrl("a", "prospectus", 7)).toBe("/api/ipos/a/pages/7?doc=prospectus");
    expect(pageUrl("a", "rhp", 7, 160)).toBe("/api/ipos/a/pages/7?doc=rhp&w=160");
  });
});
