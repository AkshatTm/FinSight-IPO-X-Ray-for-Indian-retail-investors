"use client";

import { Pause, Play } from "@phosphor-icons/react";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { useReducedMotion } from "@/components/chat/AnswerText";
import { MarkIcon } from "@/components/facts/VerdictMark";
import { formatMoney } from "@/lib/format";
import { REEL_PAGE } from "@/lib/reel";
import { useT } from "@/lib/useT";
import { CAM_END, CARD, CHIP, CYCLE, END, PHASES, STAGE_END, TRACKS } from "./reelTracks";

const pct = (n: number) => `${n * 100}%`;
const V = REEL_PAGE.value;
const PAD = { x: 0.008, y: 0.004 };
const valueBox: CSSProperties = { left: pct(V.x - PAD.x), top: pct(V.y - PAD.y), width: pct(V.w + 2 * PAD.x), height: pct(V.h + 2 * PAD.y) };

/**
 * The hero reel: a made-up prospectus page is read top to bottom, the camera pushes in on the
 * total issue size, the figure is lifted off the page, and it lands on a fact card with its verdict
 * and page while the page keeps a highlighter mark. One WAAPI timeline (CYCLE ms) drives every
 * element; it pauses off screen, in a hidden tab, or on request. Reduced motion shows the end state.
 */
export function ProspectusReel() {
  const { t } = useT();
  const reduced = useReducedMotion();
  const root = useRef<HTMLDivElement>(null);
  const anims = useRef<Animation[]>([]);
  const [paused, setPaused] = useState(false);
  const pausedRef = useRef(paused);
  const visible = useRef(true);
  const value = formatMoney(REEL_PAGE.amountInr, "crore");

  useEffect(() => {
    const el = root.current;
    if (!el || reduced || typeof el.animate !== "function") return;
    anims.current = [...el.querySelectorAll<HTMLElement>("[data-k]")].flatMap((n) => {
      const kf = TRACKS[n.dataset.k ?? ""];
      return kf ? [n.animate(kf, { duration: CYCLE, iterations: Infinity, fill: "both" })] : [];
    });
    const sync = () => {
      const run = visible.current && !pausedRef.current && document.visibilityState === "visible";
      anims.current.forEach((a) => (run ? a.play() : a.pause()));
    };
    const io = new IntersectionObserver(([e]) => {
      visible.current = e.isIntersecting;
      sync();
    });
    io.observe(el);
    document.addEventListener("visibilitychange", sync);
    return () => {
      io.disconnect();
      document.removeEventListener("visibilitychange", sync);
      anims.current.forEach((a) => a.cancel());
      anims.current = [];
    };
  }, [reduced]);

  const toggle = () => {
    pausedRef.current = !paused;
    setPaused(!paused);
    anims.current.forEach((a) => (paused ? a.play() : a.pause()));
  };

  // The server render and reduced motion both show the finished state; the timeline takes over on mount.
  return (
    <figure ref={root} className="reel relative mx-auto w-full max-w-[560px]">
      <div className="relative">
      <div aria-hidden className="absolute inset-x-[3%] -bottom-[14px] top-3 rounded-[6px] bg-[#d9d4c9] opacity-40" />
      <div aria-hidden className="absolute inset-x-[1.5%] -bottom-[7px] top-2 rounded-[6px] bg-[#ebe7de] opacity-70" />
      <div
        role="img"
        aria-label={t("land.reel.alt", { value })}
        className="reel-frame relative overflow-hidden rounded-[6px] bg-[#fbfaf6] shadow-[0_30px_80px_rgba(0,0,0,0.55),0_0_0_1px_rgba(255,255,255,0.08)]"
        style={{ aspectRatio: `${REEL_PAGE.width} / ${REEL_PAGE.height}` }}
      >
        <div data-k="stage" className="absolute inset-0 origin-top-left will-change-transform" style={{ transform: STAGE_END }}>
          {/* eslint-disable-next-line @next/next/no-img-element -- a generated, made-up page */}
          <img src={REEL_PAGE.src} alt="" width={REEL_PAGE.width} height={REEL_PAGE.height} className="h-full w-full select-none" draggable={false} />
          <div data-k="scan" className="pointer-events-none absolute inset-0" style={{ opacity: 0 }}>
            <div className="reel-scan absolute inset-x-0 top-0 h-[14%] -translate-y-full" />
          </div>
          <div data-k="dim" className="absolute rounded-[2px] shadow-[0_0_0_200vmax_rgba(23,22,26,0.5)]" style={{ ...valueBox, opacity: 0.4 }} />
          <div data-k="mark" className="reel-mark absolute origin-left rounded-[2px]" style={valueBox} />
          <div data-k="bracket" className="reel-bracket absolute" style={valueBox} />
          <div className="absolute overflow-hidden" style={valueBox}>
            <div data-k="beam" className="reel-beam absolute inset-y-0 left-0 w-[22%]" style={{ opacity: 0 }} />
          </div>
        </div>

        <div
          data-k="wire"
          aria-hidden
          className="absolute h-[1.5px] origin-right bg-stamp"
          style={{ left: pct(CARD.left + CARD.width), width: pct(END.x - CAM_END.s * PAD.x - CARD.left - CARD.width), top: pct(CARD.cy) }}
        />

        <div
          data-k="chip"
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{ opacity: 0, transformOrigin: `${pct(CHIP.x + CHIP.w / 2)} ${pct(CHIP.y + CHIP.h / 2)}` }}
        >
          <span
            className="reel-chip absolute flex items-center justify-center rounded-[4px] font-semibold"
            style={{ left: pct(CHIP.x), top: pct(CHIP.y), width: pct(CHIP.w), height: pct(CHIP.h) }}
          >
            <span className="num">{value}</span>
          </span>
        </div>

        <div
          data-k="card"
          className="reel-card absolute rounded-[8px] bg-surface p-[3.2cqw] text-text shadow-[0_14px_36px_rgba(23,22,26,0.28)] ring-1 ring-black/5"
          style={{ left: pct(CARD.left), width: pct(CARD.width), top: pct(CARD.cy), transform: "translateY(-50%)" }}
        >
          <p className="reel-t-sm text-muted">{t("land.reel.label")}</p>
          <p className="reel-t-lg num mt-[0.6cqw] font-semibold tracking-tight">{value}</p>
          <div data-k="verdict" className="mt-[1.4cqw] flex flex-wrap items-center gap-x-[2cqw] gap-y-1">
            <span className="reel-t-sm inline-flex items-center gap-1 font-medium text-ok">
              <MarkIcon state="verified" size={14} />
              {t("verdict.verified")}
            </span>
            <span className="reel-t-sm rounded-[4px] bg-surface-2 px-[1.2cqw] py-[0.3cqw] text-muted">
              {t("facts.chip", { doc: t("doc.rhpShort"), n: REEL_PAGE.page })}
            </span>
          </div>
        </div>
      </div>
      </div>

      <figcaption className="mt-7 flex items-center gap-4">
        <ol className="grid flex-1 grid-cols-4 gap-2" aria-label={t("land.reel.steps")}>
          {PHASES.map((p) => (
            <li key={p.key} className="min-w-0">
              <span data-k={`label-${p.key}`} className="block truncate text-sm text-on-band">
                {t(`land.reel.step.${p.key}`)}
              </span>
              <span className="mt-1.5 block h-[2px] overflow-hidden rounded-full bg-white/12">
                <span data-k={`step-${p.key}`} className="block h-full origin-left bg-stamp" />
              </span>
            </li>
          ))}
        </ol>
        {!reduced && (
          <button
            type="button"
            onClick={toggle}
            aria-label={paused ? t("land.reel.play") : t("land.reel.pause")}
            aria-pressed={paused}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-on-band-muted transition-[color,transform] duration-150 hover:text-on-band active:scale-[0.96]"
          >
            {paused ? <Play size={16} weight="fill" /> : <Pause size={16} weight="fill" />}
          </button>
        )}
      </figcaption>
      <p className="mt-3 text-sm text-on-band-muted">{t("land.reel.note")}</p>
    </figure>
  );
}
