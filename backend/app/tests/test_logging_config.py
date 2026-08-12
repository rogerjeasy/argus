import io
import logging
from collections.abc import Iterator

import pytest

from app.core.logging_config import configure_logging


@pytest.fixture
def captured_log() -> Iterator[io.StringIO]:
    """Point the Argus root handler at a buffer, then restore the real config."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    stream = io.StringIO()
    configure_logging(stream=stream, force=True)
    try:
        yield stream
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)


def test_info_from_ws_session_module_reaches_stdout_with_extra_fields(
    captured_log: io.StringIO,
) -> None:
    # The exact call `app/ws/session.py` makes on a successful connect.
    logging.getLogger("app.ws.session").info(
        "ws_session_connected",
        extra={"session_id": "session-abc", "uid": "user-1"},
    )

    output = captured_log.getvalue()
    assert "ws_session_connected" in output
    assert "app.ws.session" in output
    assert "INFO" in output
    assert "session_id=session-abc" in output
    assert "uid=user-1" in output


def test_records_without_context_fields_still_format(captured_log: io.StringIO) -> None:
    logging.getLogger("app.core.clients").info("plain message")

    output = captured_log.getvalue()
    assert "plain message" in output
    assert "session_id=" not in output


def test_exception_extra_fields_survive_the_formatter(captured_log: io.StringIO) -> None:
    logger = logging.getLogger("app.ws.session")
    try:
        raise RuntimeError("gemini unreachable")
    except RuntimeError:
        logger.exception(
            "ws_session_connect_failed",
            extra={"session_id": "session-xyz", "uid": "user-2"},
        )

    output = captured_log.getvalue()
    assert "ws_session_connect_failed" in output
    assert "session_id=session-xyz" in output
    assert "uid=user-2" in output
    assert "RuntimeError: gemini unreachable" in output


def test_configure_logging_is_idempotent() -> None:
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    try:
        configure_logging(stream=io.StringIO(), force=True)
        before = len(root.handlers)
        configure_logging()
        configure_logging()
        assert len(root.handlers) == before
    finally:
        root.handlers = saved_handlers
        root.setLevel(saved_level)
