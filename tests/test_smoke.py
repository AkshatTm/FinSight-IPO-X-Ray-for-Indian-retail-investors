import importlib

import pytest

import vidura

PACKAGES = [
    "core", "ingest", "parse", "normalize", "extract", "weaklabel", "retrieve", "generate",
    "verify", "guard", "chat", "evaluate", "api", "pipeline",
]  # fmt: skip


def test_version_is_set() -> None:
    assert vidura.__version__


@pytest.mark.parametrize("package", PACKAGES)
def test_package_imports_and_has_docstring(package: str) -> None:
    module = importlib.import_module(f"vidura.{package}")
    assert module.__doc__, f"vidura.{package} needs a responsibility docstring"
