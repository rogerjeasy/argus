"""Root logging configuration.

Without this, Python's root logger defaults to WARNING with no handler, so every
``logger.info(...)`` in the WebSocket session lifecycle (connect / first audio
frame / disconnect) is silently discarded, and the ``extra={...}`` fields
attached to warnings and exceptions never reach the output at all — the default
formatter only renders ``%(message)s``-style fields it is told about.

Cloud Run captures anything written to stdout/stderr into Cloud Logging, so a
single stdout handler at INFO is all "structured logging reaches stdout" needs
in Phase 0. The formatter below appends the small, known set of contextual
fields this codebase passes via ``extra=`` (see ``app/ws/session.py``) whenever
they are present, which keeps records greppable without pulling in a generic
JSON-logging framework.
"""

import logging
import sys
from typing import TextIO

#: Contextual fields this codebase attaches via ``logger.*(..., extra={...})``.
#: Rendered as ``key=value`` suffixes, and only when the record actually carries
#: them — referencing them directly in a format string would raise for every
#: third-party log record that does not.
CONTEXT_FIELDS: tuple[str, ...] = ("session_id", "uid", "status")

_BASE_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_HANDLER_NAME = "argus-stdout"


class ContextFieldFormatter(logging.Formatter):
    """Formatter that appends any :data:`CONTEXT_FIELDS` carried by a record."""

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        context = " ".join(
            f"{field}={getattr(record, field)}"
            for field in CONTEXT_FIELDS
            if hasattr(record, field)
        )
        return f"{formatted} {context}" if context else formatted


def configure_logging(
    level: int = logging.INFO,
    stream: TextIO | None = None,
    force: bool = False,
) -> None:
    """Attach a single stdout handler to the root logger at ``level``.

    Idempotent: repeated calls (``create_app()`` runs on import and again in
    tests) will not stack duplicate handlers. Pass ``force=True`` to replace an
    existing Argus handler, which is how tests redirect output to a buffer.
    """
    root = logging.getLogger()
    existing = next((h for h in root.handlers if h.get_name() == _HANDLER_NAME), None)
    if existing is not None:
        if not force:
            root.setLevel(level)
            return
        root.removeHandler(existing)
        existing.close()

    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(ContextFieldFormatter(_BASE_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)
