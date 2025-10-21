"""Project-wide logging configuration helpers."""

from __future__ import annotations

import logging
import os
from typing import Optional

LOG_LEVEL_ENV = "GLOBUS_LOG_LEVEL"

# Default format keeps timestamps compact while still showing module and message.
DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _resolve_level(value: Optional[str]) -> int:
    """Translate a string log level into the corresponding logging constant."""
    if not value:
        return logging.INFO

    value = value.strip().upper()
    if value.isdigit():
        return int(value)

    level = getattr(logging, value, None)
    if isinstance(level, int):
        return level

    raise ValueError(f"Unsupported log level: {value}")


def setup_logging() -> None:
    """Initialise root logging handlers with sane defaults.

    The log level can be overridden via the ``GLOBUS_LOG_LEVEL`` environment
    variable, accepting either the standard textual levels (e.g. ``DEBUG``) or
    a numeric value.
    """
    root_logger = logging.getLogger()

    # Respect pre-existing configuration to avoid duplicating output during tests.
    if root_logger.handlers:
        return

    level = _resolve_level(os.getenv(LOG_LEVEL_ENV))
    logging.basicConfig(level=level, format=DEFAULT_LOG_FORMAT)
