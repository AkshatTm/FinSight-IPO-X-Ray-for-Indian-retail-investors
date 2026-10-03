"""Writes tests/fixtures/fake_bank.parquet: a tiny risk bank with known neighbours (B2.2a).

    uv run python tests/fixtures/make_fake_bank.py

Ten companies (2018-2023) and 32-dimensional vectors built from 4 "topics": every company has a
debt risk (topic 0); companies A-E also have a customer-concentration risk (topic 1); only
company A has a cyber risk (topic 2). Company J's rows are from 2024 (outside the reference
years) and repeat topic 3, which nobody else has. Small random noise keeps rows distinct.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

OUT = Path(__file__).with_name("fake_bank.parquet")
DIM = 32


def topic(k: int) -> np.ndarray:
    v = np.zeros(DIM, dtype=np.float32)
    v[k * 4 : k * 4 + 4] = 1.0
    return v / np.linalg.norm(v)


def rows() -> list[dict[str, object]]:
    rng = np.random.default_rng(2026)
    out: list[dict[str, object]] = []

    def add(company: str, year: int, title: str, k: int) -> None:
        v = topic(k) + rng.normal(0, 0.02, DIM).astype(np.float32)
        out.append(
            {
                "company": company,
                "year": year,
                "title": title,
                "embedding": (v / np.linalg.norm(v)).astype(np.float32).tolist(),
            }
        )

    for i, name in enumerate("ABCDEFGHI"):
        company = f"Company {name} Limited"
        year = 2018 + i % 6
        add(company, year, f"{name}: we have significant borrowings", 0)
        if name in "ABCDE":
            add(company, year, f"{name}: we depend on a few customers", 1)
        if name == "A":
            add(company, year, "A: a cyber attack could disrupt us", 2)
    add("Company J Limited", 2024, "J: drone rules may change", 3)
    add("Company J Limited", 2024, "J: drone rules may change again", 3)
    return out


def main() -> None:
    data = rows()
    table = pa.table(
        {
            "company": [r["company"] for r in data],
            "year": pa.array([r["year"] for r in data], pa.int32()),
            "title": [r["title"] for r in data],
            "embedding": pa.array([r["embedding"] for r in data], pa.list_(pa.float32())),
        }
    )
    pq.write_table(table, OUT)
    print("wrote", OUT, OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
