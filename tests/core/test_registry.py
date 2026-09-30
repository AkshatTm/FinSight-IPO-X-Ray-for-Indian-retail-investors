import pytest

from finsight.core import registry


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    registry.clear()


def test_register_and_get_by_name() -> None:
    @registry.register("extractor", "dummy")
    class Dummy:
        name = "dummy"

    instance = registry.get("extractor", "dummy")
    assert isinstance(instance, Dummy)


def test_instantiation_is_lazy_and_cached() -> None:
    calls: list[int] = []

    @registry.register("llm", "counting")
    class Counting:
        def __init__(self) -> None:
            calls.append(1)

    assert calls == []  # registering must not construct anything
    first = registry.get("llm", "counting")
    second = registry.get("llm", "counting")
    assert first is second
    assert calls == [1]


def test_get_passes_constructor_kwargs_on_first_use() -> None:
    @registry.register("asr", "configurable")
    class Configurable:
        def __init__(self, size: str = "small") -> None:
            self.size = size

    assert registry.get("asr", "configurable", size="tiny").size == "tiny"  # type: ignore[attr-defined]


def test_unknown_name_lists_available_choices() -> None:
    @registry.register("extractor", "rules")
    class Rules:
        pass

    with pytest.raises(KeyError, match="rules"):
        registry.get("extractor", "missing")


def test_unknown_kind_is_rejected() -> None:
    with pytest.raises(ValueError, match="kind"):
        registry.register("not_a_kind", "x")


def test_duplicate_registration_is_rejected() -> None:
    @registry.register("reranker", "same")
    class One:
        pass

    with pytest.raises(ValueError, match="already registered"):

        @registry.register("reranker", "same")
        class Two:
            pass


def test_available_lists_registered_names() -> None:
    @registry.register("verifier_check", "b")
    class B:
        pass

    @registry.register("verifier_check", "a")
    class A:
        pass

    assert registry.available("verifier_check") == ["a", "b"]
