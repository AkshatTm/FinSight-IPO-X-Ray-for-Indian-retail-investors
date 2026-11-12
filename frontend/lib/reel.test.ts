import { describe, expect, it } from "vitest";
import { camera, onFrame, REEL_PAGE } from "./reel";

describe("reel camera", () => {
  it("is the identity at zoom 1", () => {
    expect(camera(0.7, 0.8, 1)).toEqual({ tx: 0, ty: 0, s: 1 });
  });

  it("centres the target when the page edge allows it", () => {
    const cam = camera(0.5, 0.5, 2);
    const b = onFrame({ x: 0.5, y: 0.5, w: 0, h: 0 }, cam);
    expect(b.x).toBeCloseTo(0.5);
    expect(b.y).toBeCloseTo(0.5);
  });

  it("never shows past the page edge", () => {
    const cam = camera(0.99, 0.99, 3);
    expect(cam.tx).toBeCloseTo(-200);
    expect(cam.ty).toBeCloseTo(-200);
  });

  it("keeps the issue-size figure inside the frame when zoomed", () => {
    const v = REEL_PAGE.value;
    const b = onFrame(v, camera(v.x + v.w / 2, v.y + v.h / 2, 2.4));
    expect(b.x).toBeGreaterThan(0);
    expect(b.y).toBeGreaterThan(0);
    expect(b.x + b.w).toBeLessThan(1);
    expect(b.y + b.h).toBeLessThan(1);
  });
});
