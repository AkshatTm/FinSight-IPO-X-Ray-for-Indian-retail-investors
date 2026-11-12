/**
 * The hero reel: one made-up prospectus page (generated, public/landing/prospectus-top.webp) and
 * where its "Total issue size" figure sits on it, as fractions of the image. Swap the image and
 * these boxes together; nothing else knows the page.
 */
export const REEL_PAGE = {
  src: "/landing/prospectus-top.webp",
  width: 1696,
  height: 1395,
  page: 1,
  /** The printed figure "₹ 1,260.00 crore" (image px 1050-1288 x 1084-1127). */
  value: { x: 1050 / 1696, y: 1084 / 1395, w: 238 / 1696, h: 43 / 1395 },
  /** Total issue size in rupees, as the page prints it. */
  amountInr: "12600000000",
} as const;

export type Box = { x: number; y: number; w: number; h: number };

/**
 * Camera that puts the point (cx, cy) of the page at the centre of the frame at zoom `s`, with
 * transform-origin 0 0. Clamped so the page edge never shows. Returns translate in % of the page.
 */
export function camera(cx: number, cy: number, s: number): { tx: number; ty: number; s: number } {
  const clamp = (v: number) => Math.min(0, Math.max(1 - s, v));
  return { tx: clamp(0.5 - s * cx) * 100, ty: clamp(0.5 - s * cy) * 100, s };
}

/** Where a page box lands in the frame under a camera, as fractions of the frame. */
export function onFrame(b: Box, cam: { tx: number; ty: number; s: number }): Box {
  return { x: cam.tx / 100 + cam.s * b.x, y: cam.ty / 100 + cam.s * b.y, w: cam.s * b.w, h: cam.s * b.h };
}
