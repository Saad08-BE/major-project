"""Operational logging that deliberately avoids raw healthcare content."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_directory: Path, debug: bool = False) -> logging.Logger:
    """Configure a local log with event metadata only, never prompts or document text."""
    log_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("healthcare_intelligence")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    if logger.handlers:
        return logger
    handler = logging.FileHandler(log_directory / "application.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger

