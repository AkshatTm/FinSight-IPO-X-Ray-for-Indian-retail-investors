"""Name-to-implementation registry so config, not imports, chooses a backend.

Packages never import each other's concrete classes. An implementation registers
itself with a decorator; callers ask for it by kind and name. Instantiation is
lazy (first ``get``) and cached, so heavy models load only when used.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

KINDS = ("extractor", "verifier_check", "llm", "asr", "reranker", "doc_adapter")

T = TypeVar("T")

_classes: dict[str, dict[str, Callable[..., Any]]] = {kind: {} for kind in KINDS}
_instances: dict[tuple[str, str], Any] = {}


def _check_kind(kind: str) -> None:
    if kind not in _classes:
        raise ValueError(f"Unknown registry kind {kind!r}; expected one of {KINDS}")


def register(kind: str, name: str) -> Callable[[T], T]:
    """Class decorator: ``@register("extractor", "rules")``."""
    _check_kind(kind)

    def decorator(factory: T) -> T:
        if name in _classes[kind]:
            raise ValueError(f"{kind} {name!r} is already registered")
        _classes[kind][name] = factory  # type: ignore[assignment]
        return factory

    return decorator


def get(kind: str, name: str, **kwargs: Any) -> Any:
    """Return the (cached) instance for ``kind``/``name``, creating it on first use."""
    _check_kind(kind)
    key = (kind, name)
    if key not in _instances:
        try:
            factory = _classes[kind][name]
        except KeyError:
            raise KeyError(
                f"No {kind} named {name!r}. Available: {available(kind) or 'none registered'}"
            ) from None
        _instances[key] = factory(**kwargs)
    return _instances[key]


def available(kind: str) -> list[str]:
    """Registered names of one component kind, sorted."""
    _check_kind(kind)
    return sorted(_classes[kind])


def clear() -> None:
    """Forget every registration and instance (used by tests)."""
    for names in _classes.values():
        names.clear()
    _instances.clear()
