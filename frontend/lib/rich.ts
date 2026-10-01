/** Splits copy that marks glossary terms as `[[id|text]]` into plain and term parts. */
export type RichPart = { text: string; term?: string };

export function parseRich(input: string): RichPart[] {
  const parts: RichPart[] = [];
  const re = /\[\[([a-z_]+)\|([^\]]+)\]\]/g;
  let last = 0;
  for (const m of input.matchAll(re)) {
    const at = m.index ?? 0;
    if (at > last) parts.push({ text: input.slice(last, at) });
    parts.push({ text: m[2], term: m[1] });
    last = at + m[0].length;
  }
  if (last < input.length) parts.push({ text: input.slice(last) });
  return parts;
}
