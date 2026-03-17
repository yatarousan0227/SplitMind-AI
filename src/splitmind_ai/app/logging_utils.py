"""Logging helpers for verbose runtime diagnostics."""

from __future__ import annotations

import logging
import os
from typing import Any


def configure_logging(default_level: str = "DEBUG") -> None:
    """Configure root logging once, defaulting to verbose diagnostics."""
    level_name = os.environ.get("SPLITMIND_LOG_LEVEL", default_level).upper()
    level = getattr(logging, level_name, logging.DEBUG)

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        )
    else:
        root.setLevel(level)


def preview_text(value: Any, limit: int = 120) -> str:
    """Return a compact one-line preview for logs."""
    if value is None:
        return ""
    text = str(value).replace("\n", "\\n")
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."
