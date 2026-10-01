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
