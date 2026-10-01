"""ASR bake-off (E12, ADR-021): which Whisper size transcribes Hindi questions best on CPU?

    uv run --group asr python scripts/asr_bakeoff.py make-references   # once: draft the references
    uv run --group asr python scripts/asr_bakeoff.py run --models small,medium,large-v3-turbo

Clips: ``data/raw/audio/hi_q01..hi_q10.m4a`` (local, never committed; hi_q02 is the demo clip).
Per candidate: character error rate (primary; spaces ignored), word error rate, seconds to
transcribe each clip, real-time factor, load time and memory. The PRD target is a 5 s clip in at
most 6 s on the CPU (01 section 7).

**The references are drafts.** ``reference`` is the raw machine draft, ``reference_corrected`` my
reading of what was said (names and spellings fixed from context); CER uses the corrected one and
``cer_vs_raw_draft`` the other. Nobody has typed what was said in the clips, so ``make-references``
transcribes them with the largest candidate (``reference_source``; matching them to known questions
was tried and dropped: the clips name companies, and a near-identical question about another IPO is
a wrong reference). Akshat edits
``data/gold/asr_references.csv`` and fills ``reviewed_by_akshat``; until then every CER here is
measured against a machine draft and is **optimistic for the model that drafted it**. Nothing in
this script edits a hypothesis.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from pathlib import Path
from typing import Any

from finsight.core.config import get_settings
from finsight.voice import FasterWhisperBackend, cer, cer_with_spaces, wer

CLIPS = [f"hi_q{n:02d}" for n in range(1, 11)]
DRAFT_MODEL = "large-v3-turbo"
FIELDS = ["clip", "reference", "reference_corrected", "reference_source", "reviewed_by_akshat"]


def audio_dir() -> Path:
    return get_settings().paths.data_dir / "raw" / "audio"


def references_path() -> Path:
    return get_settings().paths.data_dir / "gold" / "asr_references.csv"


def make_references() -> None:
    path = references_path()
    if path.exists():
        raise SystemExit(f"{path} exists: edit it by hand instead of regenerating it")
    asr = FasterWhisperBackend(DRAFT_MODEL)
    rows = []
    for clip in CLIPS:
        text = asr.transcribe(audio_dir() / f"{clip}.m4a")
        reference, source = text, f"asr_draft_{DRAFT_MODEL}"
        rows.append({"clip": clip, "reference": reference, "reference_corrected": "",
                     "reference_source": source, "reviewed_by_akshat": ""})  # fmt: skip
        print(clip, source, "|", text)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {path}: Akshat to check every row and fill reviewed_by_akshat")


def load_references() -> dict[str, dict[str, str]]:
    with references_path().open(encoding="utf-8-sig", newline="") as fh:
        return {r["clip"]: r for r in csv.DictReader(fh)}


def rss_mb() -> float | None:
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / 2**20)
    except ImportError:
        return None


def run_model(name: str, refs: dict[str, dict[str, str]], compute_type: str) -> dict[str, Any]:
    before = rss_mb()
    asr = FasterWhisperBackend(name, compute_type=compute_type)
    load_s = asr.load()
    clips = []
    for clip in CLIPS:
        started = time.perf_counter()
        result = asr.transcribe_detailed(audio_dir() / f"{clip}.m4a")
        wall = time.perf_counter() - started
        draft = refs[clip]["reference"]
        ref = refs[clip].get("reference_corrected") or draft  # the corrected reading is primary
        clips.append({"clip": clip, "hypothesis": result.text, "reference": ref,
                      "reference_source": refs[clip]["reference_source"],
                      "cer": round(cer(ref, result.text), 4),
                      "cer_vs_raw_draft": round(cer(draft, result.text), 4),
                      "cer_with_spaces": round(cer_with_spaces(ref, result.text), 4),
                      "wer": round(wer(ref, result.text), 4),
                      "audio_s": round(result.duration_s, 2), "seconds": round(wall, 2)})  # fmt: skip
        print(name, clip, f"cer {clips[-1]['cer']:.3f}", f"{wall:.1f}s", flush=True)
    after = rss_mb()
    seconds = [c["seconds"] for c in clips]
    audio = sum(c["audio_s"] for c in clips)
    summary = {
        "mean_cer": round(statistics.mean(c["cer"] for c in clips), 4),
        "median_cer": round(statistics.median(c["cer"] for c in clips), 4),
        "mean_cer_vs_raw_draft": round(statistics.mean(c["cer_vs_raw_draft"] for c in clips), 4),
        "mean_wer": round(statistics.mean(c["wer"] for c in clips), 4),
        "median_seconds_per_clip": statistics.median(seconds),
        "max_seconds_per_clip": max(seconds),
        "first_clip_seconds": seconds[0],
        "real_time_factor": round(sum(seconds) / audio, 2) if audio else None,
        "mean_audio_s": round(audio / len(clips), 2),
        "load_s": round(load_s, 1),
        "rss_mb_before": before, "rss_mb_after_load_and_run": after,
    }  # fmt: skip
    return {"summary": summary, "clips": clips}


def run(models: list[str], compute_type: str) -> None:
    refs = load_references()
    sources = sorted({r["reference_source"].split("(")[0] for r in refs.values()})
    reviewed = sum(bool(r["reviewed_by_akshat"].strip()) for r in refs.values())
    report: dict[str, Any] = {
        "compute_type": compute_type, "device": "cpu", "n_clips": len(CLIPS),
        "references_reviewed_by_akshat": f"{reviewed}/{len(refs)}",
        "reference_sources": sources, "draft_model": DRAFT_MODEL,
        "note": "no reference has been reviewed by Akshat: `reference` is the raw Whisper draft "
                f"({DRAFT_MODEL}), `reference_corrected` (primary) is Claude Code's reading of what "
                "was said; CER against either is optimistic for the drafting model",
        "run_at": time.strftime("%Y-%m-%d %H:%M"), "models": {},
    }  # fmt: skip
    out = get_settings().paths.eval_dir / "asr.json"
    if out.exists():
        report["models"] = json.loads(out.read_text(encoding="utf-8")).get("models", {})
    for name in models:
        report["models"][name] = run_model(name, refs, compute_type)
        print(name, json.dumps(report["models"][name]["summary"]), flush=True)
        out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("make-references")
    run_p = sub.add_parser("run")
    run_p.add_argument("--models", default="small,medium,large-v3-turbo")
    run_p.add_argument("--compute-type", default="int8")
    args = parser.parse_args()
    if args.cmd == "make-references":
        make_references()
    else:
        run(args.models.split(","), args.compute_type)


if __name__ == "__main__":
    main()
