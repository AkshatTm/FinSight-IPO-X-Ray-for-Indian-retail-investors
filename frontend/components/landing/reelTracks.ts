import { camera, onFrame, REEL_PAGE } from "@/lib/reel";

/** One loop of the hero reel, in ms. Every track below shares it, so they stay in step. */
export const CYCLE = 10_000;
export const ZOOM = 2.4;

const EIO = "cubic-bezier(0.77, 0, 0.175, 1)"; // on-screen movement
const EO = "cubic-bezier(0.23, 1, 0.32, 1)"; // things arriving

const v = REEL_PAGE.value;
export const CAM = camera(v.x + v.w / 2, v.y + v.h / 2, ZOOM);
/** The resting shot after the pull: the offer table, close enough that the marked figure reads. */
export const CAM_END = camera(0.55, 0.72, 1.45);
const tf = (c: { tx: number; ty: number; s: number }) => `translate(${c.tx}%, ${c.ty}%) scale(${c.s})`;
const T1 = tf({ tx: 0, ty: 0, s: 1 });
const TZ = tf(CAM);
const TE = tf(CAM_END);
/** The stage transform for the finished state (server render, reduced motion). */
export const STAGE_END = TE;

/** Where the figure sits in the frame while zoomed: the extracted chip starts exactly there. */
export const CHIP = onFrame(v, CAM);
/** Where the figure sits in the frame in the resting shot. */
export const END = onFrame(v, CAM_END);
/** The fact card's anchor (frame fractions), level with the marked figure. */
export const CARD = { left: 0.035, width: 0.42, cy: END.y + END.h / 2 };
const chipCx = CHIP.x + CHIP.w / 2;
const chipCy = CHIP.y + CHIP.h / 2;
const toCard = `translate(${(CARD.left + 0.15 - chipCx) * 100}%, ${(CARD.cy + 0.01 - chipCy) * 100}%) scale(0.5)`;

type Frame = Keyframe & { offset: number };
const f = (offset: number, props: Keyframe, easing?: string): Frame => ({ ...props, ...(easing ? { easing } : {}), offset });

/** The phases, as shares of the loop; the step bar under the page follows them. */
export const PHASES = [
  { key: "read", from: 0.02, to: 0.16 },
  { key: "find", from: 0.16, to: 0.3 },
  { key: "extract", from: 0.3, to: 0.5 },
  { key: "check", from: 0.58, to: 0.68 },
] as const;

const fadeOut = (props: Keyframe, rest: Keyframe): Frame[] => [f(0.93, props, EO), f(0.99, rest), f(1, rest)];

/** Keyframes per `data-k` element. Offsets are shares of CYCLE. */
export const TRACKS: Record<string, Frame[]> = {
  stage: [
    f(0, { transform: T1 }),
    f(0.16, { transform: T1 }, EIO),
    f(0.3, { transform: TZ }),
    f(0.48, { transform: TZ }, EIO),
    f(0.6, { transform: TE }),
    f(0.93, { transform: TE }, EIO),
    f(1, { transform: T1 }),
  ],
  scan: [
    f(0, { opacity: 0, transform: "translateY(0%)" }),
    f(0.02, { opacity: 1, transform: "translateY(0%)" }, "linear"),
    f(0.15, { opacity: 1, transform: "translateY(100%)" }),
    f(0.17, { opacity: 0, transform: "translateY(100%)" }),
    f(1, { opacity: 0, transform: "translateY(100%)" }),
  ],
  dim: [
    f(0, { opacity: 0 }),
    f(0.26, { opacity: 0 }, EO),
    f(0.32, { opacity: 1 }),
    f(0.49, { opacity: 1 }, EO),
    f(0.58, { opacity: 0.4 }),
    f(0.93, { opacity: 0.4 }, EO),
    f(0.99, { opacity: 0 }),
    f(1, { opacity: 0 }),
  ],
  bracket: [
    f(0, { opacity: 0, clipPath: "inset(-6px 100% -6px -6px)" }),
    f(0.3, { opacity: 1, clipPath: "inset(-6px 100% -6px -6px)" }, EIO),
    f(0.34, { opacity: 1, clipPath: "inset(-6px -6px -6px -6px)" }),
    ...fadeOut({ opacity: 1, clipPath: "inset(-6px -6px -6px -6px)" }, { opacity: 0, clipPath: "inset(-6px -6px -6px -6px)" }),
  ],
  beam: [
    f(0, { opacity: 0, transform: "translateX(-120%)" }),
    f(0.34, { opacity: 1, transform: "translateX(-120%)" }, "cubic-bezier(0.45, 0, 0.55, 1)"),
    f(0.43, { opacity: 1, transform: "translateX(560%)" }),
    f(0.44, { opacity: 0, transform: "translateX(560%)" }),
    f(1, { opacity: 0, transform: "translateX(560%)" }),
  ],
  chip: [
    f(0, { opacity: 0, transform: "translate(0%, 0%) scale(1)" }),
    f(0.42, { opacity: 0, transform: "translate(0%, 0%) scale(1)" }, EO),
    f(0.45, { opacity: 1, transform: "translate(0%, -2.5%) scale(1.06)" }),
    f(0.49, { opacity: 1, transform: "translate(0%, -2.5%) scale(1.06)" }, EIO),
    f(0.6, { opacity: 0.9, transform: toCard }),
    f(0.63, { opacity: 0, transform: toCard }),
    f(1, { opacity: 0, transform: toCard }),
  ],
  mark: [
    f(0, { transform: "scaleX(0)", opacity: 1 }),
    f(0.57, { transform: "scaleX(0)", opacity: 1 }, EO),
    f(0.63, { transform: "scaleX(1)", opacity: 1 }),
    ...fadeOut({ transform: "scaleX(1)", opacity: 1 }, { transform: "scaleX(1)", opacity: 0 }),
  ],
  wire: [
    f(0, { transform: "scaleX(0)", opacity: 1 }),
    f(0.6, { transform: "scaleX(0)", opacity: 1 }, EO),
    f(0.65, { transform: "scaleX(1)", opacity: 1 }),
    ...fadeOut({ transform: "scaleX(1)", opacity: 1 }, { transform: "scaleX(1)", opacity: 0 }),
  ],
  card: [
    f(0, { opacity: 0, transform: "translateY(-50%) translateY(10px) scale(0.97)" }),
    f(0.6, { opacity: 0, transform: "translateY(-50%) translateY(10px) scale(0.97)" }, EO),
    f(0.65, { opacity: 1, transform: "translateY(-50%) translateY(0px) scale(1)" }),
    ...fadeOut({ opacity: 1, transform: "translateY(-50%) translateY(0px) scale(1)" }, { opacity: 0, transform: "translateY(-50%) translateY(4px) scale(0.99)" }),
  ],
  verdict: [
    f(0, { opacity: 0, transform: "translateY(4px)" }),
    f(0.66, { opacity: 0, transform: "translateY(4px)" }, EO),
    f(0.69, { opacity: 1, transform: "translateY(0px)" }),
    f(1, { opacity: 1, transform: "translateY(0px)" }),
  ],
  ...Object.fromEntries(
    PHASES.map((p) => [
      `step-${p.key}`,
      [
        f(0, { transform: "scaleX(0)" }),
        f(p.from, { transform: "scaleX(0)" }, "linear"),
        f(p.to, { transform: "scaleX(1)" }),
        f(0.97, { transform: "scaleX(1)" }),
        f(1, { transform: "scaleX(0)" }),
      ],
    ]),
  ),
  ...Object.fromEntries(
    PHASES.map((p) => [
      `label-${p.key}`,
      [f(0, { opacity: 0.45 }), f(p.from, { opacity: 0.45 }, EO), f(p.from + 0.02, { opacity: 1 }), f(0.97, { opacity: 1 }), f(1, { opacity: 0.45 })],
    ]),
  ),
};
