"use client";

import { useEffect, useRef } from "react";
import { useChat } from "@/lib/chatStore";
import { useT } from "@/lib/useT";
import { useVoice } from "@/lib/useVoice";
import { MicButton, VoiceStatus } from "./MicButton";

interface Props {
  ipoId: string;
  disabled: boolean;
  /** `voice` is true when the text came from the microphone (and the user has checked it). */
  onSend: (q: string, voice: boolean) => void;
}

export const MAX_LEN = 300;

/** Enter sends, Shift+Enter adds a line, `/` focuses the box, 300 characters max (spec 7.5.2). */
export function Composer({ ipoId, disabled, onSend }: Props) {
  const { t } = useT();
  const draft = useChat((s) => s.drafts[ipoId]);
  const setDraft = useChat((s) => s.setDraft);
  const text = draft?.text ?? "";
  const fromVoice = draft?.voice ?? false;
  const setText = (v: string) => setDraft(ipoId, v, fromVoice && v === text);
  const voice = useVoice({
    onTranscript: (tr) => {
      setDraft(ipoId, tr.slice(0, MAX_LEN), true);
      ref.current?.focus();
    },
  });
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable) return;
      e.preventDefault();
      ref.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const send = () => {
    const q = text.trim();
    if (!q || disabled) return;
    onSend(q, fromVoice);
    setDraft(ipoId, "", false);
    voice.reset();
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        send();
      }}
      className="border-t border-rule bg-surface p-3"
    >
      <div className="flex items-end gap-2">
        <label className="min-w-0 flex-1">
          <span className="sr-only-keep">{t("ask.placeholder")}</span>
          <textarea
            ref={ref}
            rows={1}
            maxLength={MAX_LEN}
            value={text}
            placeholder={t("ask.placeholder")}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                send();
              }
            }}
            className="max-h-32 min-h-11 w-full resize-none rounded-[6px] border border-rule bg-bg px-3 py-2.5 placeholder:text-muted"
          />
        </label>
        <MicButton voice={voice} />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          className="h-11 rounded-[6px] bg-stamp px-5 text-sm font-medium text-bg disabled:opacity-40"
        >
          {t("ask.send")}
        </button>
      </div>
      <VoiceStatus voice={voice} />
      {text.length > 250 && (
        <p className="mt-1 text-right text-xs text-muted" aria-live="polite">
          {t("ask.counter", { n: text.length })}
        </p>
      )}
    </form>
  );
}
