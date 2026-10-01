import { describe, expect, it } from "vitest";
import { parseRich } from "./rich";

describe("parseRich", () => {
  it("returns plain text untouched", () => {
    expect(parseRich("No terms here.")).toEqual([{ text: "No terms here." }]);
  });
  it("splits glossary markers", () => {
    expect(parseRich("That's an [[ipo|IPO]] (initial). Open a [[demat|demat account]].")).toEqual([
      { text: "That's an " },
      { text: "IPO", term: "ipo" },
      { text: " (initial). Open a " },
      { text: "demat account", term: "demat" },
      { text: "." },
    ]);
  });
  it("handles a term at the very start and end", () => {
    expect(parseRich("[[sebi|सेबी]]")).toEqual([{ text: "सेबी", term: "sebi" }]);
  });
});
