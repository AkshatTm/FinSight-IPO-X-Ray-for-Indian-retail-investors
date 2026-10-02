"use client";

import { ArrowLeft } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";
import { AskPane } from "@/components/chat/AskPane";
import { FactsPane } from "@/components/facts/FactsPane";
import { InspectorDrawer } from "@/components/inspector/InspectorDrawer";
import { ShortcutsDialog } from "@/components/ui/ShortcutsDialog";
import { GlossaryDrawer } from "@/components/ui/GlossaryDrawer";
import { ErrorBlock } from "@/components/ui/ErrorBlock";
import { useChat } from "@/lib/chatStore";
import { useIpo, useIpos, useXray } from "@/lib/api/hooks";
import { formatDate, formatMoney, formatRupee } from "@/lib/format";
import { useUi } from "@/lib/store";
import { useLayout } from "@/lib/useBreakpoint";
import { useT } from "@/lib/useT";
import { fieldById, resolveField } from "@/lib/xray";
import { DocumentPane } from "./DocumentPane";
import { ResizablePanes } from "./ResizablePanes";
import { Tour } from "./Tour";
import { UnitToggle } from "./UnitToggle";

type Tab = "facts" | "document" | "ask";

const headBtn = "h-11 rounded-[6px] border border-rule px-3 text-sm hover:bg-surface-2";

function Header({ id }: { id: string }) {
  const { t, lang } = useT();
  const unit = useUi((s) => s.unit);
  const { data: ipos } = useIpos();
  const { data: xray } = useXray(id);
  const ipo = ipos?.find((i) => i.id === id);
  const openGlossary = useUi((s) => s.openGlossary);
  const setInspector = useUi((s) => s.setInspector);
  const answered = useChat((s) => (s.turns[id] ?? []).some((x) => x.final));
  const price = xray && fieldById(xray.fields, "offer_price");
  const r = price ? resolveField(price) : null;
  const priceText = r?.value?.kind === "money" && r.value.value_inr ? formatRupee(r.value.value_inr) : null;

  const item = (label: string, value: string | null) =>
    value ? (
      <div>
        <dt className="text-xs text-muted">{label}</dt>
        <dd className="font-medium">{value}</dd>
      </div>
    ) : null;

  return (
    <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 pb-3">
      <div className="min-w-0">
        <Link href="/ipos" className="inline-flex h-11 items-center gap-1 text-sm text-muted hover:text-text">
          <ArrowLeft size={16} /> {t("ws.back")}
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-semibold tracking-tight sm:text-2xl">{ipo?.company ?? xray?.company ?? " "}</h1>
          {ipo?.sector && <span className="hidden rounded-full border border-rule px-3 py-0.5 text-sm text-muted sm:inline">{ipo.sector}</span>}
        </div>
      </div>
      <dl className="grid w-full grid-cols-3 gap-x-4 gap-y-2 text-sm sm:flex sm:w-auto sm:flex-wrap sm:gap-x-8">
        {item(t("ws.offerPrice"), priceText)}
        {item(t("ws.issueSize"), ipo?.issue_size_inr ? formatMoney(ipo.issue_size_inr, unit, lang) : null)}
        {item(t("ws.listed"), ipo?.listing_date ? formatDate(ipo.listing_date, lang) : null)}
      </dl>
      <div className="flex max-w-full flex-wrap items-center gap-2">
        <button type="button" onClick={() => openGlossary()} className={headBtn}>{t("ws.glossary")}</button>
        <button
          type="button"
          onClick={() => setInspector(true)}
          disabled={!answered}
          title={t("ws.inspectTip")}
          aria-label={`${t("ws.inspect")}: ${t("ws.inspectTip")}`}
          className={`${headBtn} disabled:cursor-not-allowed disabled:opacity-50`}
        >
          {t("ws.inspect")}
        </button>
        <UnitToggle />
      </div>
    </div>
  );
}

function Tabs({ tabs, tab, onTab }: { tabs: Tab[]; tab: Tab; onTab: (t: Tab) => void }) {
  const { t } = useT();
  return (
    <div role="tablist" className="mb-2 flex gap-1 border-b border-rule">
      {tabs.map((k) => (
        <button
          key={k}
          type="button"
          role="tab"
          aria-selected={tab === k}
          onClick={() => onTab(k)}
          className={`h-11 border-b-2 px-4 text-sm ${tab === k ? "border-stamp font-semibold" : "border-transparent text-muted hover:text-text"}`}
        >
          {t(`ws.tab.${k}`)}
        </button>
      ))}
    </div>
  );
}

export function Workspace({ id }: { id: string }) {
  const layout = useLayout();
  const highlightNonce = useUi((s) => s.highlight?.nonce ?? 0);
  const { data: detail, error, refetch } = useIpo(id);
  const company = useIpos().data?.find((i) => i.id === id)?.company ?? "";
  const [tab, setTab] = useState<Tab>("document");
  const [rightTab, setRightTab] = useState<"facts" | "ask">("facts");
  const [seen, setSeen] = useState(highlightNonce);

  // Clicking a source in Facts or Ask on a small screen jumps to the Document tab (spec 7.1).
  if (highlightNonce !== seen) {
    setSeen(highlightNonce);
    setTab("document");
  }

  if (error) {
    return (
      <div className="py-10">
        <ErrorBlock error={error} onRetry={() => void refetch()} />
      </div>
    );
  }

  const facts = <FactsPane ipoId={id} />;
  const ask = <AskPane ipoId={id} company={company} />;
  const doc = detail ? (
    <DocumentPane ipoId={id} detail={detail} />
  ) : (
    <div className="skeleton h-full w-full" aria-busy="true" />
  );
  const paneBox = "h-full overflow-y-auto rounded-[10px] border border-rule bg-surface";
  const askBox = "h-full overflow-hidden rounded-[10px] border border-rule bg-surface";

  return (
    // On a phone the page itself must not scroll: the header stays compact and the panes take the rest.
    <div className={layout === "narrow" ? "flex h-[calc(100dvh-4.5rem)] min-h-[30rem] flex-col pt-2" : "pt-4"}>
      <Header id={id} />
      <GlossaryDrawer />
      <InspectorDrawer ipoId={id} />
      <ShortcutsDialog />
      <Tour ready={!!detail} />
      <div
        className={layout === "narrow" ? "min-h-0 flex-1" : "h-[calc(100dvh-13.5rem)] min-h-[34rem]"}
        data-layout={layout}
      >
        {layout === "wide" && (
          <ResizablePanes
            initial={[30, 40, 30]}
            minPx={[300, 420, 320]}
            panes={[<div key="f" className={paneBox}>{facts}</div>, doc, <div key="a" className={askBox}>{ask}</div>]}
          />
        )}
        {layout === "mid" && (
          <ResizablePanes
            initial={[55, 45]}
            minPx={[420, 320]}
            panes={[
              doc,
              <div key="r" className="flex h-full flex-col">
                <Tabs tabs={["facts", "ask"]} tab={rightTab} onTab={(k) => setRightTab(k as "facts" | "ask")} />
                <div className={`min-h-0 flex-1 ${rightTab === "facts" ? paneBox : askBox}`}>{rightTab === "facts" ? facts : ask}</div>
              </div>,
            ]}
          />
        )}
        {layout === "narrow" && (
          <div className="flex h-full flex-col">
            <Tabs tabs={["facts", "document", "ask"]} tab={tab} onTab={setTab} />
            <div className="min-h-0 flex-1">
              {tab === "document" ? doc : <div className={tab === "facts" ? paneBox : askBox}>{tab === "facts" ? facts : ask}</div>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
