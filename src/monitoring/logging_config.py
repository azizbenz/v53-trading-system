"""Shared rotating file handler builder for monitoring and VPS rails."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

DEFAULT_ROTATING_LOG_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_ROTATING_LOG_BACKUP_COUNT = 5


def build_rotating_file_handler(
    path: str,
    *,
    max_bytes: int = DEFAULT_ROTATING_LOG_MAX_BYTES,
    backup_count: int = DEFAULT_ROTATING_LOG_BACKUP_COUNT,
) -> RotatingFileHandler:
    """Build a UTF-8 rotating file handler with the canonical monitoring format."""

    handler = RotatingFileHandler(
        filename=path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    return handler


def build_rotating_jsonl_handler(
    path: str,
    *,
    max_bytes: int = DEFAULT_ROTATING_LOG_MAX_BYTES,
    backup_count: int = DEFAULT_ROTATING_LOG_BACKUP_COUNT,
) -> RotatingFileHandler:
    """Build a rotating JSONL handler for structured service/event logs."""

    handler = RotatingFileHandler(
        filename=path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    return handler


__all__ = [
    "DEFAULT_ROTATING_LOG_BACKUP_COUNT",
    "DEFAULT_ROTATING_LOG_MAX_BYTES",
    "build_rotating_file_handler",
    "build_rotating_jsonl_handler",
]
