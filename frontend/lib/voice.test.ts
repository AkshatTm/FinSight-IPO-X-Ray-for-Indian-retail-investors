import { describe, expect, it } from "vitest";
import { MAX_RECORD_MS, answerLanguage, voiceReducer } from "./voice";

describe("voiceReducer", () => {
  it("walks the happy path", () => {
    let s = voiceReducer("idle", { type: "tap" });
    expect(s).toBe("permission");
    s = voiceReducer(s, { type: "granted" });
    expect(s).toBe("recording");
    s = voiceReducer(s, { type: "stop", elapsedMs: 4000 });
    expect(s).toBe("transcribing");
    expect(voiceReducer(s, { type: "transcribed" })).toBe("done");
  });
  it("discards recordings over 20 s", () => {
    expect(voiceReducer("recording", { type: "stop", elapsedMs: MAX_RECORD_MS + 1 })).toBe("tooLong");
    expect(voiceReducer("recording", { type: "stop", elapsedMs: MAX_RECORD_MS })).toBe("transcribing");
  });
  it("maps denial and errors", () => {
    expect(voiceReducer("permission", { type: "denied" })).toBe("blocked");
    expect(voiceReducer("transcribing", { type: "error" })).toBe("failed");
  });
  it("ignores taps while busy and allows retry from terminal states", () => {
    expect(voiceReducer("transcribing", { type: "tap" })).toBe("transcribing");
    expect(voiceReducer("failed", { type: "tap" })).toBe("permission");
    expect(voiceReducer("done", { type: "reset" })).toBe("idle");
  });
});

describe("answerLanguage", () => {
  it("switches to Hindi for Devanagari", () => {
    expect(answerLanguage("पैसा कहाँ लगेगा", "en")).toBe("hi");
    expect(answerLanguage("where does the money go", "en")).toBe("en");
    expect(answerLanguage("where does the money go", "hi")).toBe("hi");
  });
});
