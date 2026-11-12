"""The FINSIGHT_* fallback: old names still work, new names win, one warning."""

import pytest

from vidura._legacy_env import apply_legacy_env


def test_old_name_is_copied_with_a_warning() -> None:
    env = {"FINSIGHT_PROFILE": "dev_light"}
    with pytest.warns(DeprecationWarning, match="FINSIGHT_PROFILE"):
        migrated = apply_legacy_env(env)
    assert migrated == ["FINSIGHT_PROFILE"]
    assert env["VIDURA_PROFILE"] == "dev_light"


def test_new_name_wins_and_does_not_warn(recwarn: pytest.WarningsRecorder) -> None:
    env = {"FINSIGHT_PROFILE": "old", "VIDURA_PROFILE": "new"}
    assert apply_legacy_env(env) == []
    assert env["VIDURA_PROFILE"] == "new"
    assert not recwarn.list


def test_nothing_set_is_silent(recwarn: pytest.WarningsRecorder) -> None:
    assert apply_legacy_env({"PATH": "x"}) == []
    assert not recwarn.list
