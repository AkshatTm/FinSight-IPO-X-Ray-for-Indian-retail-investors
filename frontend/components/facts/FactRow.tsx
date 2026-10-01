"use client";

import { Info } from "@phosphor-icons/react";
import { useState } from "react";
import { CHECK_LABEL, EXTRACTOR_NAME, FIELD_CONTENT, pick } from "@/lib/content/fields";
import { useWords } from "@/lib/api/hooks";
import type { Lang } from "@/lib/format";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { needsPerShare, resolveField, scalarText, sentenceAround, type XField } from "@/lib/xray";
import { MarkIcon, VerdictMark, type MarkState } from "./VerdictMark";

const docName = (doc: "rhp" | "prospectus", t: ReturnType<typeof useT>["t"]) =>
  t(doc === "rhp" ? "doc.rhpShort" : "doc.prospectusShort");

function Sentence({ ipoId, f, doc, page }: { ipoId: string; f: XField; doc: "rhp" | "prospectus"; page: number }) {
  const { data } = useWords(ipoId, doc, page, !!f.bbox && doc === f.doc);
  if (!data || !f.bbox) return null;
  const s = sentenceAround(data.words, f.bbox);
  if (!s.text) return null;
  return (
    <p className="rounded-[6px] bg-surface-2 px-2 py-1.5 text-sm">
      {s.parts.map((p, i) => (
        <span key={i} className={p.hit ? "underline decoration-stamp decoration-2 underline-offset-2" : ""}>
          {p.text}{" "}
        </span>
      ))}
    </p>
  );
}

function Popover({ ipoId, f, doc, page, lang }: { ipoId: string; f: XField; doc: "rhp" | "prospectus"; page: number; lang: Lang }) {
  const { t } = useT();
  const model = f.extractor.startsWith("qa_");
  return (
    <div
      role="tooltip"
      className="absolute left-2 right-2 top-full z-20 -mt-1 space-y-2 rounded-[10px] border border-rule bg-surface p-3 text-sm shadow-[var(--shadow-float)]"
    >
      <p className="font-medium">{t("pop.found", { doc: docName(doc, t), page })}</p>
      <Sentence ipoId={ipoId} f={f} doc={doc} page={page} />
      {f.value && "raw" in f.value && (
        <p className="text-muted">
          {t("pop.asWritten")}: <span className="font-mono text-text">{f.value.raw}</span>
        </p>
      )}
      <p className="text-muted">
        {t("pop.readBy")}: {pick(EXTRACTOR_NAME[f.extractor] ?? { en: f.extractor, hi: f.extractor }, lang)}
      </p>
      {model && (
        <div className="flex items-center gap-2 text-muted">
          <span>{t("pop.confidence")}</span>
          <span className="h-1.5 w-24 overflow-hidden rounded-full bg-surface-2">
            <span className="block h-full bg-stamp" style={{ width: `${Math.round(f.score * 100)}%` }} />
          </span>
          <span className="tabular-nums">{Math.round(f.score * 100)}%</span>
        </div>
      )}
      {f.checks.length > 0 && (
        <ul className="space-y-1">
          {f.checks.map((c) => (
            <li key={c.check} className="flex items-start gap-1.5">
              <MarkIcon state={c.status} size={14} />
              <span>{CHECK_LABEL[c.check] ? pick(CHECK_LABEL[c.check], lang) : c.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface Props {
  ipoId: string;
  field: XField;
  compare: boolean;
}

export function FactRow({ ipoId, field: f, compare }: Props) {
  const { t, lang } = useT();
  const unit = useUi((s) => s.unit);
  const setHighlight = useUi((s) => s.setHighlight);
  const [pinned, setPinned] = useState(false);
  const [hover, setHover] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const content = FIELD_CONTENT[f.field_id];
  const label = content ? pick(content.label, lang) : lang === "hi" ? f.label_hi : f.label_en;
  const r = resolveField(f);
  const isPlaceholderField = f.value?.kind === "placeholder";

  let valueNode: React.ReactNode = null;
  let valueText = "";
  if (r.notInDocument) {
    valueText = content?.notInDocument ? pick(content.notInDocument, lang) : "";
    valueNode = <span className="text-muted">{valueText}</span>;
  } else if (r.blank) {
    valueText = content?.placeholder ? pick(content.placeholder, lang) : "[●]";
    valueNode = <span className="text-muted">{valueText}</span>;
  } else if (r.value?.kind === "list") {
    const items = r.value.items;
    const shown = expanded ? items : items.slice(0, 3);
    valueText = shown.join(", ");
    valueNode = (
      <span>
        {shown.map((it, i) => (
          <span key={i} className="block">
            {it}
          </span>
        ))}
      </span>
    );
  } else if (r.value) {
    valueText = scalarText(f.field_id, r.value, unit, lang, t("facts.perShare")) ?? "";
    valueNode = (
      <span className="font-medium">
        {valueText}
        {needsPerShare(f.field_id, r.value) && <span className="ml-1 font-normal text-muted">{t("facts.perShare")}</span>}
      </span>
    );
  }

  const mark: MarkState | null = r.notInDocument
    ? null
    : isPlaceholderField
      ? "placeholder"
      : f.verdict;
  const showChip = !r.notInDocument;
  const chip = t("facts.chip", { doc: docName(r.doc, t), n: r.page });
  const sr = [label, valueText, mark ? t(`verdict.${mark}`) : "", showChip ? chip : ""].filter(Boolean).join(", ");

  const open = pinned || hover;
  const go = () => {
    if (r.notInDocument) return;
    setHighlight({
      ipoId,
      doc: r.doc,
      page: r.page,
      bbox: r.doc === f.doc ? f.bbox : null,
      kind: "source",
    });
  };

  return (
    <li
      className="relative border-b border-rule last:border-b-0"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onKeyDown={(e) => e.key === "Escape" && (setPinned(false), setHover(false))}
    >
      <div className="flex items-start gap-1">
        <button
          type="button"
          onClick={go}
          disabled={r.notInDocument}
          aria-label={`${sr}. ${r.notInDocument ? "" : t("facts.showOnPage")}`}
          className="grid min-h-11 flex-1 grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] items-start gap-x-3 gap-y-1 rounded-[6px] px-2 py-2.5 text-left hover:bg-surface-2 disabled:cursor-default disabled:hover:bg-transparent"
        >
          <span className="text-sm text-muted">
            <span className={content ? "term" : ""}>{label}</span>
          </span>
          <span className="text-right text-sm md:text-left">{valueNode}</span>
          <span className="col-span-2 flex flex-wrap items-center justify-between gap-2">
            {mark ? <VerdictMark state={mark} /> : <span />}
            {showChip && (
              <span className="rounded-full border border-rule px-2 py-0.5 text-xs text-muted">{chip}</span>
            )}
          </span>
          {r.filledInProspectus && <span className="col-span-2 text-xs text-muted">{t("facts.filled")}</span>}
        </button>
        {!r.notInDocument && (
          <button
            type="button"
            aria-expanded={open}
            aria-label={`${t("facts.details")}: ${label}`}
            onClick={() => setPinned((v) => !v)}
            onFocus={() => setHover(true)}
            onBlur={() => setHover(false)}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-[6px] text-muted hover:text-text"
          >
            <Info size={18} />
          </button>
        )}
      </div>
      {r.value?.kind === "list" && r.value.items.length > 3 && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="ml-2 h-11 px-2 text-sm text-stamp underline underline-offset-2"
        >
          {expanded ? t("facts.less") : t("facts.more", { n: r.value.items.length - 3 })}
        </button>
      )}
      {content && <span className="sr-only-keep">{pick(content.tip, lang)}</span>}
      {open && !r.notInDocument && <Popover ipoId={ipoId} f={f} doc={r.doc} page={r.page} lang={lang} />}
      {compare && f.candidates.length > 0 && (
        <ul className="mb-2 ml-4 space-y-1 border-l-2 border-rule pl-3 text-sm">
          {f.candidates.map((c) => (
            <li key={c.extractor} className="flex items-center justify-between gap-2">
              <span className="text-muted">{pick(EXTRACTOR_NAME[c.extractor] ?? { en: c.extractor, hi: c.extractor }, lang)}</span>
              <span className="flex items-center gap-1.5">
                <span className="font-mono text-xs">{c.raw}</span>
                {c.gold_match != null && <MarkIcon state={c.gold_match ? "verified" : "contradicted"} size={14} />}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
