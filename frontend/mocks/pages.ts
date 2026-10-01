// MOCK page images (SVG) for development. Real pages are WebP renders of the PDF.
// Every mock page carries one sentence at the bbox the X-Ray mocks point to.
export const MOCK_BBOX: [number, number, number, number] = [72, 410, 301, 423];

export function pageSvg(company: string, doc: string, n: number, total: number): string {
  const lines: string[] = [];
  for (let y = 120; y < 780; y += 18) {
    if (y > 395 && y < 440) continue;
    const w = 260 + ((y * 7 + n * 13) % 200);
    lines.push(`<rect x="72" y="${y}" width="${w}" height="6" rx="2" fill="#d9dde5"/>`);
  }
  const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 595 842" width="595" height="842">
<rect width="595" height="842" fill="#ffffff"/>
<text x="72" y="64" font-family="sans-serif" font-size="13" font-weight="600" fill="#18202e">${esc(company)}</text>
<text x="72" y="84" font-family="sans-serif" font-size="9" fill="#5a6578">${esc(doc.toUpperCase())} page ${n} of ${total} (mock page for development)</text>
${lines.join("\n")}
<text x="72" y="421" font-family="sans-serif" font-size="11" fill="#18202e">Fresh Issue of up to Rs. 26,260 million (mock text)</text>
<text x="297" y="820" font-family="sans-serif" font-size="9" fill="#5a6578">${n}</text>
</svg>`;
}

const SENTENCE = "Fresh Issue of up to Rs. 26,260 million (mock text)";

/** Word boxes for the mock sentence (5.4 pt per character at 11 pt). */
export function pageWords(n: number): { page: number; width: number; height: number; words: { t: string; b: [number, number, number, number] }[] } {
  let x = 72;
  const words = SENTENCE.split(" ").map((t) => {
    const w = t.length * 5.4;
    const b: [number, number, number, number] = [x, 410, x + w, 423];
    x += w + 5.4;
    return { t, b };
  });
  return { page: n, width: 595, height: 842, words };
}
