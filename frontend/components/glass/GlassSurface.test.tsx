import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GlassSurface } from "./GlassSurface";

describe("GlassSurface", () => {
  it("renders a solid surface with a rule border when glass is unsupported (jsdom)", () => {
    render(
      <GlassSurface className="x">
        <span>inside</span>
      </GlassSurface>,
    );
    const el = screen.getByText("inside").parentElement!;
    expect(el.className).toContain("border-rule");
    expect(el.className).toContain("bg-surface");
  });
  it("css mode uses the glass bar only when backdrop-filter is supported", () => {
    render(
      <GlassSurface mode="css">
        <span>on</span>
      </GlassSurface>,
    );
    expect(screen.getByText("on").parentElement!.className).toContain("glass-css");
    const spy = vi.spyOn(CSS, "supports").mockReturnValue(false);
    render(
      <GlassSurface mode="css">
        <span>bar</span>
      </GlassSurface>,
    );
    expect(screen.getByText("bar").parentElement!.className).not.toContain("glass-css");
    spy.mockRestore();
  });
});
