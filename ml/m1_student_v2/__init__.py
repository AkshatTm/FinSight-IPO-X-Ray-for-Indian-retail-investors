"""M1 Student v2 chat SFT data builder and numkeep filter package (Phase 4 — ARGON)."""

from ml.m1_student_v2.chat_sft_builder import (
    ABSTAIN_EN,
    ABSTAIN_HI,
    build_scripted_near_miss_unanswerables,
    filter_teacher_chat_rows,
    format_passage_blocks,
    mix_rewrite_and_chat_sft,
    render_chat_prompt,
)

__all__ = [
    "ABSTAIN_EN",
    "ABSTAIN_HI",
    "build_scripted_near_miss_unanswerables",
    "filter_teacher_chat_rows",
    "format_passage_blocks",
    "mix_rewrite_and_chat_sft",
    "render_chat_prompt",
]
