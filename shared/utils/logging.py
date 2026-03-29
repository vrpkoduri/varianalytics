"""Structured logging setup for all services.

JSON-formatted logs for production, human-readable for development.
"""

import logging
import sys
from typing import Optional


def setup_logging(
    service_name: str,
    level: str = "INFO",
    json_format: bool = False,
) -> logging.Logger:
    """Configure structured logging for a service.

    Args:
        service_name: Name of the service (gateway, computation, reports).
        level: Log level string.
        json_format: If True, output JSON lines. If False, human-readable.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
            '"service":"%(name)s","message":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
