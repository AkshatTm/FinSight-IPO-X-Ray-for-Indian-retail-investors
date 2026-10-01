"use client";

import { useEffect, useRef, useState } from "react";
import { GLOSSARY } from "@/lib/content/glossary";
import { useUi } from "@/lib/store";
import { useT } from "@/lib/useT";
import { Drawer } from "./Drawer";

/** Searchable list of terms in the current language; opens scrolled to the clicked term (spec 7.8). */
export function GlossaryDrawer() {
  const { t, lang } = useT();
  const { open, term } = useUi((s) => s.glossary);
  const close = useUi((s) => s.closeGlossary);
  const [q, setQ] = useState("");
  const target = useRef<HTMLLIElement | null>(null);

  const needle = q.trim().toLowerCase();
  const rows = GLOSSARY.filter((g) => !needle || `${g.title[lang]} ${g.title.en} ${g.short[lang]}`.toLowerCase().includes(needle));

  useEffect(() => {
    if (open) target.current?.scrollIntoView({ block: "start" });
  }, [open, term]);

  if (!open) return null;
  return (
    <Drawer title={t("gl.title")} onClose={close}>
      <label className="mt-4 block">
        <span className="sr-only-keep">{t("gl.search")}</span>
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("gl.search")}
          className="h-11 w-full rounded-[6px] border border-rule bg-bg px-3 placeholder:text-muted"
        />
      </label>
      {rows.length === 0 ? (
        <p className="mt-6 text-muted">{t("gl.none")}</p>
      ) : (
        <ul className="mt-4">
          {rows.map((g) => (
            <li
              key={g.id}
              ref={g.id === term ? target : undefined}
              className={`border-b border-rule py-3 ${g.id === term ? "bg-stamp/5" : ""}`}
            >
              <h3 className="font-semibold" lang={lang === "hi" ? "hi" : "en"}>{g.title[lang]}</h3>
              <p className="mt-1 text-sm text-muted" lang={lang === "hi" ? "hi" : "en"}>{g.short[lang]}</p>
            </li>
          ))}
        </ul>
      )}
    </Drawer>
  );
}
