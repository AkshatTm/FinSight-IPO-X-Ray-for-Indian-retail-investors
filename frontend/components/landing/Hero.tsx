"use client";

import Link from "next/link";
import { useRef, useState, useSyncExternalStore } from "react";
import { VerdictMark } from "@/components/facts/VerdictMark";
import { detectCssGlass } from "@/components/glass/GlassSurface";
import { useT } from "@/lib/useT";

// The fresh-issue line of Ather's RHP page 3 (public/landing/ather-rhp-p3.webp, the pipeline's own
// page image, 595.44 x 841.68 pt). The "₹26,260 MILLION" value sits at x 432.6-485.6, y 161.3-168.5
// (the X-Ray box); the lens centre is nudged left of it so the lens stays inside the page and
// still covers the value. Shares of the page, from /api/ipos/ather-energy-2025/pages/3/words.
const REST = { x: 70, y: 19.6 };
const never = () => () => {};
const calm = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function Lens() {
  const { t } = useT();
  const glass = useSyncExternalStore(never, detectCssGlass, () => false);
  const reduced = useSyncExternalStore(never, calm, () => true);
  const box = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState(REST);

  const follow = (e: React.PointerEvent) => {
    if (e.pointerType !== "mouse" || reduced || !box.current) return;
    const r = box.current.getBoundingClientRect();
    const x = Math.min(88, Math.max(12, ((e.clientX - r.left) / r.width) * 100));
    const y = Math.min(94, Math.max(6, ((e.clientY - r.top) / r.height) * 100));
    setPos({ x, y });
  };

  return (
    <div
      ref={box}
      className="relative mx-auto w-full max-w-[420px] -rotate-[1.5deg] select-none"
      style={{ aspectRatio: "595.44 / 841.68" }}
      onPointerMove={follow}
      onPointerLeave={() => setPos(REST)}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- static illustration, nothing to optimise */}
      <img
        src="/landing/ather-rhp-p3.webp"
        alt={t("land.lens.alt")}
        width={910}
        height={1286}
        className="absolute inset-0 h-full w-full rounded-[6px] border border-rule opacity-70 shadow-[var(--shadow-float)]"
        draggable={false}
      />
      <div
        className="absolute"
        style={{
          width: 220,
          height: 90,
          left: `${pos.x}%`,
          top: `${pos.y}%`,
          transform: "translate(-50%, -50%)",
          transition: "left 260ms var(--ease-out), top 260ms var(--ease-out)",
        }}
        aria-hidden
      >
        {glass ? (
          <div className="lens-css h-full w-full ring-2 ring-stamp/70" />
        ) : (
          <div className="h-9 w-full rounded-[6px] border-2 border-stamp bg-stamp/10" />
        )}
      </div>
      <p
        className="mark-in absolute left-[30%] top-[29%] inline-flex items-center gap-2 rounded-[10px] border border-rule bg-surface px-3 py-1.5 text-sm shadow-[var(--shadow-float)]"
        style={{ animationDelay: "400ms" }}
      >
        <VerdictMark state="verified" />
        <span>{t("land.lens.tag")}</span>
      </p>
    </div>
  );
}

export function Hero() {
  const { t } = useT();
  return (
    <section className="grid items-center gap-12 py-12 md:grid-cols-[1.1fr_0.9fr] md:py-20">
      <div>
        <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight md:text-[3.75rem]">{t("land.h1")}</h1>
        <p className="mt-6 max-w-xl text-lg text-muted">{t("land.sub")}</p>
        <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
          <Link
            href="/ipos"
            className="inline-flex h-12 items-center rounded-[6px] bg-stamp px-6 font-medium text-bg transition-transform duration-150 active:scale-[0.97]"
          >
            {t("land.cta")}
          </Link>
          <Link href="/how-it-works" className="inline-flex h-12 items-center text-stamp underline underline-offset-4">
            {t("land.how")}
          </Link>
        </div>
        <p className="mt-4 text-sm text-muted">{t("land.free")}</p>
      </div>
      <Lens />
    </section>
  );
}
