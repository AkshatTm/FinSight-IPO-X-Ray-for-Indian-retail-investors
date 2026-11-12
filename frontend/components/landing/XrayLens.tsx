"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useReducedMotion } from "@/components/chat/AnswerText";
import { MarkIcon } from "@/components/facts/VerdictMark";
import { useXray } from "@/lib/api/hooks";
import { FIELD_CONTENT, pick } from "@/lib/content/fields";
import { LENS_PAGE, lensSpots, spotAt, type Spot } from "@/lib/lensSpots";
import { useT } from "@/lib/useT";

const ZOOM = 2.2;
const LENS = 0.36; // lens diameter as a share of the page width
const DWELL = 1900; // ms the idle tour rests on each fact

const centre = (s: Spot) => ({ x: s.x + s.w / 2, y: s.y + s.h / 2 });

/**
 * An X-ray lens over a real RHP page. The pointer (or a tap, or Tab) moves the lens; under it the
 * page turns to film and the facts FinSight read light up with their verdicts and page. While
 * nobody touches it, the lens tours the facts by itself.
 */
export function XrayLens() {
  const { t } = useT();
  const reduced = useReducedMotion();
  const { data } = useXray(LENS_PAGE.ipo);
  const spots = useMemo(() => (data ? lensSpots(data.fields, t("facts.perShare")) : []), [data, t]);

  const page = useRef<HTMLDivElement>(null);
  const lens = useRef<HTMLDivElement>(null);
  const film = useRef<HTMLDivElement>(null);
  const tilt = useRef<HTMLDivElement>(null);
  const pos = useRef({ x: 0.5, y: 0.3 });
  const target = useRef({ x: 0.5, y: 0.3 });
  const user = useRef(0); // time of the last user move; the tour waits 4 s after it
  const [active, setActive] = useState<Spot | null>(null);
  const [found, setFound] = useState<Set<string>>(new Set());

  useEffect(() => {
    let raf = 0;
    let lastActive: string | null = null;
    const start = performance.now();
    const frame = (now: number) => {
      const el = page.current;
      if (el && lens.current && film.current) {
        const W = el.clientWidth;
        const H = el.clientHeight;
        if (user.current === -1) user.current = now;
        const idle = now - user.current > 4000;
        if (idle && spots.length && !reduced) {
          const i = Math.floor(Math.max(0, now - start) / DWELL) % (spots.length + 1);
          target.current = i < spots.length ? centre(spots[i]) : { x: 0.5, y: 0.42 };
        }
        const k = reduced ? 1 : 0.14;
        pos.current.x += (target.current.x - pos.current.x) * k;
        pos.current.y += (target.current.y - pos.current.y) * k;
        const R = (LENS * W) / 2;
        const cx = pos.current.x * W;
        const cy = pos.current.y * H;
        lens.current.style.transform = `translate3d(${cx - R}px, ${cy - R}px, 0)`;
        film.current.style.width = `${W * ZOOM}px`;
        film.current.style.height = `${H * ZOOM}px`;
        film.current.style.transform = `translate3d(${R - cx * ZOOM}px, ${R - cy * ZOOM}px, 0)`;
        if (tilt.current && !reduced) {
          tilt.current.style.transform = `rotateY(${(pos.current.x - 0.5) * 9}deg) rotateX(${(0.5 - pos.current.y) * 6}deg)`;
        }
        const hit = spotAt(spots, pos.current.x, pos.current.y, LENS / 3);
        if ((hit?.id ?? null) !== lastActive) {
          lastActive = hit?.id ?? null;
          setActive(hit);
          if (hit && !idle) setFound((s) => (s.has(hit.id) ? s : new Set(s).add(hit.id)));
        }
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [spots, reduced]);

  const moveTo = (x: number, y: number) => {
    user.current = -1; // stamped with the frame time on the next frame
    target.current = { x: Math.min(1, Math.max(0, x)), y: Math.min(1, Math.max(0, y)) };
  };
  const onPointer = (e: React.PointerEvent) => {
    const r = page.current?.getBoundingClientRect();
    if (r) moveTo((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
  };

  const label = (s: Spot) => (FIELD_CONTENT[s.id] ? pick(FIELD_CONTENT[s.id].label) : s.id);
  const total = spots.length;
  const all = total > 0 && found.size === total;

  return (
    <div className="relative mx-auto w-full max-w-[min(400px,calc((100svh-15rem)*0.707))] min-w-[280px] [perspective:1400px]">
      <p aria-live="polite" className="mb-3 flex min-h-8 items-center justify-end gap-2 text-sm text-on-band-muted">
        {total > 0 && (
          <span className={`rounded-full border px-3 py-1 ${all ? "border-stamp bg-stamp/15 text-on-band" : "border-white/15"}`}>
            {all ? t("land.lens.all", { total }) : t("land.lens.found", { n: found.size, total })}
          </span>
        )}
      </p>
      <div ref={tilt} className="[transform-style:preserve-3d]">
        <div
          ref={page}
          onPointerMove={onPointer}
          onPointerDown={onPointer}
          className="lens-page relative cursor-none touch-pan-y select-none overflow-hidden rounded-[14px] bg-white shadow-[0_40px_100px_rgba(0,0,0,0.6),0_0_0_1px_rgba(255,255,255,0.06)]"
          style={{ aspectRatio: `${LENS_PAGE.width} / ${LENS_PAGE.height}` }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- static page image from the pipeline */}
          <img src="/landing/ather-rhp-p3.webp" alt={t("land.lens.alt")} width={910} height={1286} className="h-full w-full object-cover brightness-[0.97]" draggable={false} />
          {spots.map((s) => {
            const c = centre(s);
            return (
              <button
                key={s.id}
                type="button"
                aria-label={t("land.lens.spot", { label: label(s) })}
                onFocus={() => moveTo(c.x, c.y)}
                onClick={() => moveTo(c.x, c.y)}
                className="absolute flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full focus-visible:outline-2 focus-visible:outline-stamp"
                style={{ left: `${c.x * 100}%`, top: `${c.y * 100}%` }}
              >
                {!found.has(s.id) && <span aria-hidden className="lens-ping h-3 w-3 rounded-full bg-stamp" />}
              </button>
            );
          })}
          <div ref={lens} aria-hidden className="lens pointer-events-none absolute left-0 top-0 overflow-hidden rounded-full" style={{ width: `${LENS * 100}%`, aspectRatio: "1" }}>
            <div ref={film} className="absolute left-0 top-0 origin-top-left">
              {/* eslint-disable-next-line @next/next/no-img-element -- same page, filmed */}
              <img src="/landing/ather-rhp-p3.webp" alt="" className="lens-film h-full w-full" draggable={false} />
              {spots.map((s) => (
                <span
                  key={s.id}
                  className="lens-box absolute rounded-[3px]"
                  style={{ left: `${(s.x - 0.006) * 100}%`, top: `${(s.y - 0.004) * 100}%`, width: `${(s.w + 0.012) * 100}%`, height: `${(s.h + 0.008) * 100}%` }}
                />
              ))}
            </div>
          </div>
          {active && <Callout spot={active} label={label(active)} />}
        </div>
      </div>
      <p className="mt-4 text-center text-sm text-on-band-muted">{t("land.lens.hint")}</p>
    </div>
  );
}

function Callout({ spot, label }: { spot: Spot; label: string }) {
  const { t } = useT();
  const left = spot.x + spot.w / 2 < 0.5;
  return (
    <div
      key={spot.id}
      className={`lens-callout pointer-events-none absolute z-10 w-[68%] rounded-[12px] bg-surface p-3 text-text shadow-[0_18px_40px_rgba(0,0,0,0.35)] ${left ? "left-[4%]" : "right-[4%]"}`}
      style={{ top: `${(spot.y + 0.16) * 100}%` }}
    >
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-0.5 flex items-center gap-1.5 text-lg font-semibold leading-snug">
        <MarkIcon state={spot.mark} size={18} />
        <span className="num">{spot.value}</span>
      </p>
      <p className="mt-1 text-sm text-muted">
        {spot.mark === "placeholder"
          ? spot.filled
            ? t("land.lens.blank", { value: spot.filled })
            : t("land.lens.blankNone")
          : t(`verdict.${spot.mark}`)}
      </p>
      <p className="mt-2 inline-block rounded-[6px] bg-surface-2 px-1.5 py-0.5 text-sm text-muted">
        {t("facts.chip", { doc: t("doc.rhpShort"), n: LENS_PAGE.page })}
      </p>
    </div>
  );
}
