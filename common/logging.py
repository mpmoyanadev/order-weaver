from __future__ import annotations

import logging
import sys

import structlog
from typing import Any, cast


def setup_logging(service_name: str) -> None:
    # Процессоры имеют разнородные сигнатуры, поэтому типизируем списки шире для mypy
    shared_processors: list[Any] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    processors: list[Any] = [structlog.contextvars.merge_contextvars]
    processors += shared_processors
    processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:  # type: ignore[name-defined]
    # structlog.get_logger типизирован слабо, приводим тип явно для mypy
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name or "app"))
