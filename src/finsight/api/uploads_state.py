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
from finsight.jobs import InlineLauncher, Launcher, SimplifyDrain, process_document
from finsight.risks import Simplifier
from finsight.risks import make_simplifier as make_simplifier_from
from finsight.storage import Storage, make_storage


@dataclass
class UploadState:
    """What the upload and report routes need: settings, database, storage, launcher."""

    settings: Settings
    db: Database
    storage: Storage
    launcher: Launcher
    drain: SimplifyDrain | None = None


def build_upload_state(settings: Settings) -> UploadState:
    """Wire the profile's database, storage and job launcher."""
    db, storage = make_database(settings), make_storage(settings)

    def make_simplifier() -> Simplifier:
        return make_simplifier_from(settings.simplify, settings.paths.models_dir)

    drain = SimplifyDrain(db, storage, make_simplifier)

    def work(doc_id: str, job_id: str) -> None:
        process_document(db, storage, settings, doc_id, job_id)
        drain.kick(doc_id)  # the top-N rewrites fill in while the reader looks at the report

    for doc_id in db.docs_with_queue():  # rewrites queued before a restart carry on
        drain.kick(doc_id)
    launcher: Launcher = InlineLauncher(work)
    return UploadState(settings, db, storage, launcher, drain)


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
