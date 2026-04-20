"""Shared rotating file handler builder for monitoring and VPS rails."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler


def build_rotating_file_handler(
    path: str,
    *,
    max_bytes: int = 50_000_000,
    backup_count: int = 10,
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


__all__ = ["build_rotating_file_handler"]
