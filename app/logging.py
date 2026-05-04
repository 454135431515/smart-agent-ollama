"""Logging configuration for Smart Agent.

Call setup_logging() once at application startup (main.py).
Everywhere else: from app.logging import get_logger; logger = get_logger(__name__)

Two outputs:
  - logs/agent.jsonl  — one JSON object per line, all levels (DEBUG+)
  - stderr            — human-readable, WARNING+ only (avoids polluting the REPL)
"""

import logging
import sys
from pathlib import Path

import structlog

_SHARED_PROCESSORS: list = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
]


def setup_logging(log_dir: str = "logs") -> None:
    Path(log_dir).mkdir(exist_ok=True)

    structlog.configure(
        processors=_SHARED_PROCESSORS
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    file_handler = logging.FileHandler(f"{log_dir}/agent.jsonl", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=_SHARED_PROCESSORS,
            processor=structlog.processors.JSONRenderer(),
        )
    )

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=_SHARED_PROCESSORS,
            processor=structlog.dev.ConsoleRenderer(colors=False),
        )
    )

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(stderr_handler)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
