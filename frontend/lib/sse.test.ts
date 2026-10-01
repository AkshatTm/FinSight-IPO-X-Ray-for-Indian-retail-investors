import fc from "fast-check";
import { describe, expect, it } from "vitest";
import { SseParser, toChatEvent } from "./sse";

const wire = 'event: stage\ndata: {"name":"guard","status":"start","ms":null}\n\nevent: token\ndata: {"text":"The fresh"}\n\n';

describe("SseParser", () => {
  it("parses complete messages", () => {
    const out = new SseParser().push(wire);
    expect(out).toEqual([
      { event: "stage", data: '{"name":"guard","status":"start","ms":null}' },
      { event: "token", data: '{"text":"The fresh"}' },
    ]);
  });
  it("handles CRLF, comments, multi-line data and a missing space after the colon", () => {
    const p = new SseParser();
    const out = p.push(": keep-alive\r\nevent:token\r\ndata:{\"a\":\r\ndata:1}\r\n\r\n");
    expect(out).toEqual([{ event: "token", data: '{"a":\n1}' }]);
  });
  it("gives the same messages however the stream is cut into chunks (property)", () => {
    const expected = new SseParser().push(wire);
    fc.assert(
      fc.property(fc.array(fc.integer({ min: 1, max: wire.length - 1 }), { maxLength: 6 }), (cuts) => {
        const points = [...new Set(cuts)].sort((a, b) => a - b);
        const p = new SseParser();
        const got = [];
        let prev = 0;
        for (const c of [...points, wire.length]) {
          got.push(...p.push(wire.slice(prev, c)));
          prev = c;
        }
        expect(got).toEqual(expected);
      }),
    );
  });
  it("does not emit a message until the blank line arrives", () => {
    const p = new SseParser();
    expect(p.push('event: final\ndata: {"trace_id":"t"}\n')).toEqual([]);
    expect(p.push("\n")).toHaveLength(1);
  });
});

describe("toChatEvent", () => {
  it("types known events and drops unknown or broken ones", () => {
    expect(toChatEvent({ event: "token", data: '{"text":"x"}' })).toEqual({ event: "token", data: { text: "x" } });
    expect(toChatEvent({ event: "mystery", data: "{}" })).toBeNull();
    expect(toChatEvent({ event: "token", data: "{not json" })).toBeNull();
  });
});
