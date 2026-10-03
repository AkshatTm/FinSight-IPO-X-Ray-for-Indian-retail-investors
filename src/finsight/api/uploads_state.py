"""Shared pieces for the Phase 2 routes: database, storage, job launcher and the caller.

``get_upload_state`` is a FastAPI dependency; tests override it with a temporary SQLite
database, local storage and a synchronous launcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header

from finsight.api.errors import ApiError
from finsight.auth import AuthError, User, user_from_header
from finsight.core.config import Settings, get_settings
from finsight.db import Database, make_database
from finsight.jobs import InlineLauncher, Launcher, cloud_run_launcher, process_document
from finsight.storage import Storage, make_storage


@dataclass
class UploadState:
    """What the upload and report routes need: settings, database, storage, launcher."""

    settings: Settings
    db: Database
    storage: Storage
    launcher: Launcher


def build_upload_state(settings: Settings) -> UploadState:
    """Wire the profile's database, storage and job launcher."""
    db, storage = make_database(settings), make_storage(settings)
    launcher: Launcher
    if settings.jobs.runner == "cloud_run":
        launcher = cloud_run_launcher(settings.jobs.cpu_job_name)
    else:
        launcher = InlineLauncher(
            lambda doc_id, job_id: process_document(db, storage, settings, doc_id, job_id)
        )
    return UploadState(settings, db, storage, launcher)


@lru_cache(maxsize=1)
def get_upload_state() -> UploadState:
    """The cached upload state (a FastAPI dependency)."""
    return build_upload_state(get_settings())


UState = Annotated[UploadState, Depends(get_upload_state)]


def current_user(state: UState, authorization: Annotated[str | None, Header()] = None) -> User:
    """The signed-in caller (401 ``unauthorized`` when the token is missing or invalid)."""
    try:
        user = user_from_header(authorization, state.settings.auth)
    except AuthError as err:
        raise ApiError(401, "unauthorized", "Please sign in with Google to upload.") from err
    state.db.upsert_user(user.id, user.email)
    return user


CurrentUser = Annotated[User, Depends(current_user)]
