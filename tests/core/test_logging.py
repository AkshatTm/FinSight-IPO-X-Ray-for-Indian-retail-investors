import io
import json
import logging

from finsight.core.logging import JsonFormatter, configure_logging, get_logger, log_stage


def _capture() -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    configure_logging("INFO", stream=stream)
    return get_logger("finsight.test"), stream


def test_each_line_is_one_json_object() -> None:
    logger, stream = _capture()
    logger.info("hello")
    record = json.loads(stream.getvalue().strip())
    assert record["msg"] == "hello"
    assert record["level"] == "INFO"
    assert record["logger"] == "finsight.test"
    assert "ts" in record


def test_log_stage_emits_trace_id_stage_and_timing() -> None:
    logger, stream = _capture()
    log_stage(logger, "01TRACE", "retrieving", ms=410, n_passages=5)
    record = json.loads(stream.getvalue().strip())
    assert record["trace_id"] == "01TRACE"
    assert record["stage"] == "retrieving"
    assert record["ms"] == 410
    assert record["n_passages"] == 5


def test_exceptions_are_serialised_not_raised() -> None:
    logger, stream = _capture()
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logger.exception("failed")
    record = json.loads(stream.getvalue().strip())
    assert "RuntimeError: boom" in record["exc"]


def test_configure_logging_is_idempotent() -> None:
    _, stream = _capture()
    logger = get_logger("finsight.test")
    configure_logging("INFO", stream=stream)
    logger.info("once")
    assert len(stream.getvalue().strip().splitlines()) == 1


def test_formatter_handles_non_serialisable_extras() -> None:
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "m", None, None)
    record.weird = object()  # type: ignore[attr-defined]
    assert "weird" in JsonFormatter().format(record)
