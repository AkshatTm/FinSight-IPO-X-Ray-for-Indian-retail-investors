import importlib

import pytest

import finsight

PACKAGES = [
    "core", "ingest", "parse", "normalize", "extract", "weaklabel", "retrieve", "generate",
    "verify", "guard", "voice", "chat", "evaluate", "api", "pipeline",
]  # fmt: skip


def test_version_is_set() -> None:
    assert finsight.__version__


@pytest.mark.parametrize("package", PACKAGES)
def test_package_imports_and_has_docstring(package: str) -> None:
    module = importlib.import_module(f"finsight.{package}")
    assert module.__doc__, f"finsight.{package} needs a responsibility docstring"
