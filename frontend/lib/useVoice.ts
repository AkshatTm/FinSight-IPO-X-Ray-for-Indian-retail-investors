"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { MAX_RECORD_MS, pickMime, voiceReducer, type VoiceState } from "@/lib/voice";

interface Options {
  onTranscript: (text: string) => void;
}

export interface VoiceApi {
  state: VoiceState;
  elapsedMs: number;
  level: number;
  toggle: () => void;
  reset: () => void;
}

async function upload(blob: Blob): Promise<string> {
  const body = new FormData();
  body.append("audio", blob, "question.webm");
  body.append("language", "hi");
  const res = await fetch("/api/voice", { method: "POST", body });
  if (!res.ok) throw new ApiError("voice_failed", "voice failed", res.status);
  const data = (await res.json()) as { transcript?: string };
  const text = (data.transcript ?? "").trim();
  if (!text) throw new ApiError("empty_transcript", "empty transcript", 422);
  return text;
}

/** Records up to 20 s with MediaRecorder, posts the clip to /api/voice, hands back the transcript. */
export function useVoice({ onTranscript }: Options): VoiceApi {
  const [state, dispatch] = useReducer(voiceReducer, "idle" as VoiceState);
  const [elapsedMs, setElapsed] = useState(0);
  const [level, setLevel] = useState(0);
  const rec = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const chunks = useRef<Blob[]>([]);
  const started = useRef(0);
  const timer = useRef<number | null>(null);
  const raf = useRef<number | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const cb = useRef(onTranscript);
  useEffect(() => {
    cb.current = onTranscript;
  });

  const cleanup = useCallback(() => {
    if (timer.current) window.clearInterval(timer.current);
    if (raf.current) cancelAnimationFrame(raf.current);
    timer.current = raf.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    void ctx.current?.close().catch(() => {});
    ctx.current = null;
    setLevel(0);
  }, []);

  useEffect(() => cleanup, [cleanup]);

  const stop = useCallback(() => {
    if (rec.current && rec.current.state !== "inactive") rec.current.stop();
  }, []);

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      dispatch({ type: "denied" });
      return;
    }
    let media: MediaStream;
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      dispatch({ type: "denied" });
      return;
    }
    stream.current = media;
    chunks.current = [];
    const mime = pickMime();
    const r = new MediaRecorder(media, mime ? { mimeType: mime } : undefined);
    rec.current = r;
    r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
    r.onstop = () => {
      const elapsed = Date.now() - started.current;
      cleanup();
      dispatch({ type: "stop", elapsedMs: elapsed });
      if (elapsed > MAX_RECORD_MS) return;
      void upload(new Blob(chunks.current, { type: r.mimeType || "audio/webm" }))
        .then((text) => {
          dispatch({ type: "transcribed" });
          cb.current(text);
        })
        .catch(() => dispatch({ type: "error" }));
    };
    started.current = Date.now();
    setElapsed(0);
    dispatch({ type: "granted" });
    r.start();
    timer.current = window.setInterval(() => {
      const ms = Date.now() - started.current;
      setElapsed(ms);
      // Hard stop just under the cap so a clip is never rejected for length.
      if (ms >= MAX_RECORD_MS - 100) stop();
    }, 100);
    try {
      const AC = window.AudioContext;
      const ac = new AC();
      ctx.current = ac;
      const an = ac.createAnalyser();
      an.fftSize = 256;
      ac.createMediaStreamSource(media).connect(an);
      const buf = new Uint8Array(an.frequencyBinCount);
      const tick = () => {
        an.getByteTimeDomainData(buf);
        let peak = 0;
        for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
        setLevel(Math.min(1, peak / 64));
        raf.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // The level meter is decoration; recording works without it.
    }
  }, [cleanup, stop]);

  const toggle = useCallback(() => {
    if (state === "recording") return stop();
    if (state === "permission" || state === "transcribing") return;
    dispatch({ type: "tap" });
    void start();
  }, [state, start, stop]);

  const reset = useCallback(() => dispatch({ type: "reset" }), []);

  return { state, elapsedMs, level, toggle, reset };
}
