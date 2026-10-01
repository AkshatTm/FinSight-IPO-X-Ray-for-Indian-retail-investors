import type { Schemas } from "@/lib/api/client";
import { ApiError } from "@/lib/api/client";

type S = Schemas;

/** Typed events of POST /api/chat (docs/06_API_CONTRACT.md). */
export type ChatEvent =
  | { event: "stage"; data: S["StageEvent"] }
  | { event: "guard"; data: S["GuardEvent"] }
  | { event: "retrieval"; data: S["RetrievalEvent"] }
  | { event: "abstain"; data: S["AbstainEvent"] }
  | { event: "token"; data: S["TokenEvent"] }
  | { event: "answer"; data: S["AnswerEvent"] }
  | { event: "verdict"; data: S["VerdictEvent"] }
  | { event: "final"; data: S["FinalEvent"] }
  | { event: "error"; data: S["ErrorEvent"] };

const KNOWN = new Set(["stage", "guard", "retrieval", "abstain", "token", "answer", "verdict", "final", "error"]);

export interface RawSse {
  event: string;
  data: string;
}

/** Incremental Server-Sent Events parser: feed it chunks, get complete messages back. */
export class SseParser {
  private buf = "";
  private event = "";
  private data: string[] = [];

  push(chunk: string): RawSse[] {
    this.buf += chunk;
    const out: RawSse[] = [];
    let nl: number;
    while ((nl = this.buf.search(/\r\n|\n|\r/)) !== -1) {
      const m = /^(\r\n|\n|\r)/.exec(this.buf.slice(nl));
      const eol = m ? m[0].length : 1;
      // A lone "\r" at the very end may be the first half of "\r\n": wait for more input.
      if (this.buf[nl] === "\r" && nl + 1 === this.buf.length) break;
      const line = this.buf.slice(0, nl);
      this.buf = this.buf.slice(nl + eol);
      if (line === "") {
        if (this.data.length) out.push({ event: this.event || "message", data: this.data.join("\n") });
        this.event = "";
        this.data = [];
      } else if (line.startsWith(":")) {
        /* comment / keep-alive */
      } else {
        const i = line.indexOf(":");
        const field = i === -1 ? line : line.slice(0, i);
        let value = i === -1 ? "" : line.slice(i + 1);
        if (value.startsWith(" ")) value = value.slice(1);
        if (field === "event") this.event = value;
        else if (field === "data") this.data.push(value);
      }
    }
    return out;
  }
}

export function toChatEvent(m: RawSse): ChatEvent | null {
  if (!KNOWN.has(m.event)) return null;
  try {
    return { event: m.event, data: JSON.parse(m.data) } as ChatEvent;
  } catch {
    return null;
  }
}

/** POST /api/chat and yield typed events as they arrive. Throws ApiError for HTTP errors. */
export async function* streamChat(
  req: S["ChatRequest"],
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
  let res: Response;
  try {
    res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(req),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") return;
    throw new ApiError("network", "network", 0);
  }
  if (!res.ok || !res.body) {
    let code = "internal_error";
    try {
      const b = (await res.json()) as Partial<S["ErrorResponse"]>;
      if (b.error?.code) code = b.error.code;
    } catch {
      /* not JSON */
    }
    throw new ApiError(code, res.statusText, res.status);
  }
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  const parser = new SseParser();
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const raw of parser.push(value)) {
        const ev = toChatEvent(raw);
        if (ev) yield ev;
      }
    }
  } catch (e) {
    if ((e as Error).name === "AbortError") return;
    throw new ApiError("network", "network", 0);
  }
}
