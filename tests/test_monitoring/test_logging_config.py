from __future__ import annotations

from logging.handlers import RotatingFileHandler
from pathlib import Path

from monitoring.logging_config import (
    DEFAULT_ROTATING_LOG_BACKUP_COUNT,
    DEFAULT_ROTATING_LOG_MAX_BYTES,
    build_rotating_file_handler,
)


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


def test_build_rotating_file_handler_uses_canonical_5mb_x_5_defaults() -> None:
    log_path = Path("build_logging_config_default_shadow.log")
    handler = build_rotating_file_handler(str(log_path))

    try:
        assert isinstance(handler, RotatingFileHandler)
        assert handler.maxBytes == DEFAULT_ROTATING_LOG_MAX_BYTES
        assert handler.backupCount == DEFAULT_ROTATING_LOG_BACKUP_COUNT
        assert handler.maxBytes == 5 * 1024 * 1024
        assert handler.backupCount == 5
    finally:
        handler.close()
