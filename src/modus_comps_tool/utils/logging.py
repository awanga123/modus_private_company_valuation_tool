from __future__ import annotations

import logging
from typing import Any, Mapping

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configure application-wide structured logging."""

    shared_processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
    )


def get_logger(name: str | None = None) -> "structlog.stdlib.BoundLogger":
    return structlog.get_logger(name)

