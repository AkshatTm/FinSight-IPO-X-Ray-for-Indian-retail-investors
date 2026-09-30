"""FastAPI application factory (ADR-024: contract first).

``uv run poe api`` serves ``app``; ``uv run poe gen-openapi`` writes ``openapi.json``.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from finsight import __version__
from finsight.api.errors import ApiError, ErrorBody, ErrorResponse
from finsight.api.events import EVENT_MODELS
from finsight.api.routes import router
from finsight.core.logging import get_logger

logger = get_logger("finsight.api")


def _envelope(status_code: int, body: ErrorBody) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=ErrorResponse(error=body).model_dump())


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _envelope(exc.status_code, exc.body)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(part) for part in first.get("loc", ()))
        body = ErrorBody(
            code="validation_error",
            message=f"Invalid request: {first.get('msg', 'bad input')} ({where}).",
            hint="Check the request against /openapi.json.",
        )
        return _envelope(422, body)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error")  # the stack trace stays in the logs only
        body = ErrorBody(
            code="internal_error",
            message="Something went wrong on our side.",
            hint="Try again in a moment.",
        )
        return _envelope(500, body)


def _with_sse_events(schema: dict[str, Any]) -> dict[str, Any]:
    """Register each SSE event model as an OpenAPI component and map it on /api/chat.

    OpenAPI cannot describe the payloads of a streaming response, so without this the
    frontend would get no generated type for any event.
    """
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    refs: dict[str, dict[str, str]] = {}
    for event, model in EVENT_MODELS.items():
        model_schema = model.model_json_schema(ref_template="#/components/schemas/{model}")
        components.update(model_schema.pop("$defs", {}))
        components[model.__name__] = model_schema
        refs[event] = {"$ref": f"#/components/schemas/{model.__name__}"}
    ok_response = schema["paths"]["/api/chat"]["post"]["responses"]["200"]
    ok_response["content"]["text/event-stream"]["x-sse-events"] = refs
    return schema


def create_app() -> FastAPI:
    app = FastAPI(
        title="FinSight API",
        version=__version__,
        description="IPO X-Ray and verified chat. Contract: docs/06_API_CONTRACT.md.",
    )
    app.include_router(router)
    _install_error_handlers(app)

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = get_openapi(
                title=app.title,
                version=app.version,
                description=app.description,
                routes=app.routes,
            )
            app.openapi_schema = _with_sse_events(schema)
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]
    return app


app = create_app()
