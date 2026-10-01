"use client";

import dynamic from "next/dynamic";
import { useEffect, useSyncExternalStore, type CSSProperties, type ReactNode } from "react";

// Lazy-loaded: the library never enters the first bundle (spec 2.6).
const LiquidGlass = dynamic(() => import("liquid-glass-react"), { ssr: false });

/** CSS-only glass (blur + edge highlight) works in every browser that has backdrop-filter. */
export function detectCssGlass(): boolean {
  if (typeof window === "undefined") return false;
  const mq = (q: string) => window.matchMedia?.(q).matches ?? false;
  if (mq("(prefers-reduced-motion: reduce)")) return false;
  if (mq("(prefers-reduced-transparency: reduce)")) return false;
  return CSS.supports("backdrop-filter", "blur(1px)");
}

/** Glass only where it can look right; everything else gets a solid surface (spec 2.6). */
export function detectGlassSupport(): boolean {
  if (typeof window === "undefined") return false;
  const mq = (q: string) => window.matchMedia?.(q).matches ?? false;
  if (mq("(prefers-reduced-motion: reduce)")) return false;
  if (mq("(prefers-reduced-transparency: reduce)")) return false;
  if (!CSS.supports("backdrop-filter", "blur(1px)")) return false;
  // The SVG displacement filter used by the library only renders properly in Chromium.
  const brands = (navigator as Navigator & { userAgentData?: { brands: { brand: string }[] } })
    .userAgentData?.brands;
  return !!brands?.some((b) => b.brand === "Chromium");
}

let mounted = 0;
const subscribeNever = () => () => {};

interface Props {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  cornerRadius?: number;
  /** Inner padding passed to the glass; the fallback uses the same value. */
  padding?: string;
  onClick?: () => void;
  /** Force the solid fallback (tests, or when the glass budget of 3 is spent). */
  solid?: boolean;
  /**
   * "library": liquid-glass-react (refraction; compact elements only, it positions itself).
   * "css": blur + edge highlight for full-width bars, where the library's layout does not fit.
   */
  mode?: "library" | "css";
}

/**
 * The only way glass is used in the app. Solid surface with a 1 px rule on first paint and in
 * every fallback case; the glass layer replaces it after mount when the browser can render it.
 */
export function GlassSurface({
  children,
  className = "",
  style,
  cornerRadius = 16,
  padding = "0px",
  onClick,
  solid = false,
  mode = "library",
}: Props) {
  const supported = useSyncExternalStore(
    subscribeNever,
    mode === "css" ? detectCssGlass : detectGlassSupport,
    () => false,
  );
  const glass = supported && !solid;

  useEffect(() => {
    if (!glass) return;
    mounted += 1;
    if (mounted > 3 && process.env.NODE_ENV !== "production") {
      console.warn("GlassSurface: more than 3 glass elements mounted (spec 2.6 allows 3)");
    }
    return () => {
      mounted -= 1;
    };
  }, [glass]);

  if (glass && mode === "css") {
    return (
      <div
        className={`glass-css ${className}`}
        style={{ borderRadius: cornerRadius, padding, ...style }}
        onClick={onClick}
      >
        {children}
      </div>
    );
  }
  if (!glass) {
    return (
      <div
        className={`border border-rule bg-surface ${className}`}
        style={{ borderRadius: cornerRadius, padding, ...style }}
        onClick={onClick}
      >
        {children}
      </div>
    );
  }
  return (
    <LiquidGlass
      className={className}
      style={{ position: "relative", top: "auto", left: "auto", transform: "none", ...style }}
      cornerRadius={cornerRadius}
      padding={padding}
      displacementScale={40}
      blurAmount={0.6}
      saturation={120}
      aberrationIntensity={1}
      elasticity={0.15}
      onClick={onClick}
    >
      {children}
    </LiquidGlass>
  );
}
