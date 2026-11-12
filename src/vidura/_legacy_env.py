"""Backward compatibility for the old ``FINSIGHT_*`` environment variables.

Vidura was called FinSight. Every setting is now read from ``VIDURA_*``; a variable that is
only set under its old ``FINSIGHT_*`` name is copied to the new name at import time, so
existing ``.env`` files, deployments and CI keep working. The new name always wins. A
single deprecation warning names the variables that were migrated. The fallback is permanent.
"""

from __future__ import annotations

import os
import warnings

OLD_PREFIX = "FINSIGHT_"
NEW_PREFIX = "VIDURA_"


def apply_legacy_env(environ: dict[str, str] | None = None) -> list[str]:
    """Copy ``FINSIGHT_X`` to ``VIDURA_X`` when only the old name is set.

    Args:
        environ: The mapping to update (defaults to ``os.environ``).

    Returns:
        The old names that were migrated (empty when nothing used the old prefix).
    """
    env = os.environ if environ is None else environ
    migrated: list[str] = []
    for old in [k for k in env if k.upper().startswith(OLD_PREFIX)]:
        new = NEW_PREFIX + old[len(OLD_PREFIX) :]
        if new not in env:
            env[new] = env[old]
            migrated.append(old)
    if migrated:
        warnings.warn(
            "Deprecated environment variable name(s) "
            + ", ".join(sorted(migrated))
            + f": use the {NEW_PREFIX} prefix instead (the {OLD_PREFIX} names still work).",
            DeprecationWarning,
            stacklevel=2,
        )
    return migrated
