"use client";

import { parseRich } from "@/lib/rich";
import { GlossaryTerm } from "./GlossaryTerm";

/** Renders copy with `[[id|text]]` markers as glossary terms. */
export function Rich({ text }: { text: string }) {
  return (
    <>
      {parseRich(text).map((p, i) =>
        p.term ? (
          <GlossaryTerm key={i} id={p.term}>
            {p.text}
          </GlossaryTerm>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
    </>
  );
}
