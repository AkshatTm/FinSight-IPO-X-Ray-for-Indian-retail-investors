"""PDF to text, words, page images, sections and tables."""

from finsight.parse.clean import read_printed_page
from finsight.parse.page_images import render_pages
from finsight.parse.pdf_text import parse_pdf
from finsight.parse.sections import KEY_SECTIONS, find_sections
from finsight.parse.tables import (
    Backend,
    default_backend,
    extract_tables,
    is_pure_ofs,
    objects_table,
    pymupdf_backend,
    table_rows,
)

__all__ = [
    "KEY_SECTIONS",
    "Backend",
    "default_backend",
    "extract_tables",
    "find_sections",
    "is_pure_ofs",
    "objects_table",
    "parse_pdf",
    "pymupdf_backend",
    "read_printed_page",
    "render_pages",
    "table_rows",
]
