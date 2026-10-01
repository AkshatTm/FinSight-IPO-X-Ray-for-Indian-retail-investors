import { describe, expect, it } from "vitest";
import { resizePair } from "./ResizablePanes";

describe("resizePair", () => {
  const min = [300, 420, 320];
  it("moves the boundary and keeps the total", () => {
    const r = resizePair([30, 40, 30], 0, 5, 1400, min);
    expect(r[0]).toBeCloseTo(35);
    expect(r[1]).toBeCloseTo(35);
    expect(r[2]).toBe(30);
  });
  it("never shrinks a neighbour below its minimum width", () => {
    const left = resizePair([30, 40, 30], 0, -50, 1400, min);
    expect((left[0] / 100) * 1400).toBeCloseTo(300);
    const right = resizePair([30, 40, 30], 0, 50, 1400, min);
    expect((right[1] / 100) * 1400).toBeCloseTo(420);
  });
});
