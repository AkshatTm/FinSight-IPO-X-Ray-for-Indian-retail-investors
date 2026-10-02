import { describe, expect, it } from "vitest";
import { newTurn, type Turn } from "./chat";
import { firstContradicted, isDemoSearch, isTypingTarget, stepForKey, trickQuestion } from "./demo";

const key = (k: string, mods: Partial<KeyboardEvent> = {}) => ({ key: k, ctrlKey: false, metaKey: false, altKey: false, ...mods });

describe("demo hotkeys", () => {
  it("maps 0 to 7 and nothing else", () => {
    expect([..."01234567"].map((k) => stepForKey(key(k)))).toEqual([0, 1, 2, 3, 4, 5, 6, 7]);
    expect(stepForKey(key("8"))).toBeNull();
    expect(stepForKey(key("a"))).toBeNull();
    expect(stepForKey(key("10"))).toBeNull();
  });
  it("leaves browser shortcuts alone", () => {
    expect(stepForKey(key("1", { ctrlKey: true }))).toBeNull();
    expect(stepForKey(key("2", { metaKey: true }))).toBeNull();
    expect(stepForKey(key("3", { altKey: true }))).toBeNull();
  });
  it("ignores typing in fields", () => {
    expect(isTypingTarget(document.createElement("textarea"))).toBe(true);
    expect(isTypingTarget(document.createElement("input"))).toBe(true);
    expect(isTypingTarget(document.createElement("button"))).toBe(false);
    expect(isTypingTarget(null)).toBe(false);
  });
});

describe("demo helpers", () => {
  it("detects the flag", () => {
    expect(isDemoSearch("?demo=1")).toBe(true);
    expect(isDemoSearch("?a=b&demo=1")).toBe(true);
    expect(isDemoSearch("?demo=0")).toBe(false);
    expect(isDemoSearch("")).toBe(false);
  });
  it("picks the trick question from the suggestions", () => {
    expect(trickQuestion([{ text: "a", kind: "normal" }, { text: "Is it X?", kind: "trick" }])).toBe("Is it X?");
    expect(trickQuestion([])).toBeNull();
    expect(trickQuestion(undefined)).toBeNull();
  });
  it("finds the first contradicted number", () => {
    const t = newTurn("t1", "x", "q", "en");
    expect(firstContradicted(t)).toBeNull();
    const v = (index: number, status: string) => ({ index, status }) as unknown as Turn["verdicts"][number];
    t.verdicts = [v(0, "verified"), v(1, "contradicted"), v(2, "contradicted")];
    expect(firstContradicted(t)).toBe(1);
    expect(firstContradicted(undefined)).toBeNull();
  });
});
