import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[0] / "fixtures"))

from make_fixture_pdf import build, build_table_pdf


@pytest.fixture(scope="session")
def fixture_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build(tmp_path_factory.mktemp("pdf") / "acme-2025.pdf")


@pytest.fixture(scope="session")
def table_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_table_pdf(tmp_path_factory.mktemp("pdf") / "acme-tables-2025.pdf")
