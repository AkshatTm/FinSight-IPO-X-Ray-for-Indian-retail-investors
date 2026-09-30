"""Render PDF pages to WebP for the document viewer (ADR-010: images + word boxes).

~110 DPI at quality 80 keeps a 600-page RHP around 100 MB and is sharp on a laptop screen.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pymupdf
from PIL import Image

DEFAULT_DPI = 110
DEFAULT_QUALITY = 80


def render_pages(
    pdf_path: Path,
    out_dir: Path,
    dpi: int = DEFAULT_DPI,
    quality: int = DEFAULT_QUALITY,
    pages: Iterable[int] | None = None,
) -> list[Path]:
    """Write ``<out_dir>/<n>.webp`` for each PDF page ``n`` (1-indexed); return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with pymupdf.open(pdf_path) as pdf:
        numbers = list(pages) if pages is not None else range(1, pdf.page_count + 1)
        for n in numbers:
            pix = pdf[n - 1].get_pixmap(dpi=dpi, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            target = out_dir / f"{n}.webp"
            image.save(target, "WEBP", quality=quality, method=4)
            written.append(target)
    return written
