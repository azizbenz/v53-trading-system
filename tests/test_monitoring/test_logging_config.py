from __future__ import annotations

from logging.handlers import RotatingFileHandler
from pathlib import Path

from monitoring.logging_config import build_rotating_file_handler


def test_build_rotating_file_handler_uses_utf8_and_requested_limits() -> None:
    log_path = Path("build_logging_config_test_shadow.log")
    handler = build_rotating_file_handler(
        str(log_path),
        max_bytes=4096,
        backup_count=3,
    )

    try:
        assert isinstance(handler, RotatingFileHandler)
        assert handler.maxBytes == 4096
        assert handler.backupCount == 3
        assert handler.encoding == "utf-8"
        assert handler.formatter is not None
    finally:
        handler.close()
