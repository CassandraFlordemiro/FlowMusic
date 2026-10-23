# -*- coding: utf-8 -*-
"""
FlowMusic 360 - High Performance Rotating Logger.
Outputs to logs/flowmusic.log with a 5MB limit and 2 backups.
Eliminates scattered print statements and prevents disk bloat.
"""

import logging
from logging.handlers import RotatingFileHandler
import os

from .config import LOGS_DIR

_loggers = {}


def get_logger(name: str = "FlowMusic") -> logging.Logger:
    """Returns a configured logger instance with rotating file and optional console handler."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        # Rotating File Handler (5 MB max, 2 backups)
        log_file = os.path.join(LOGS_DIR, "flowmusic.log")
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,
                backupCount=2,
                encoding="utf-8",
                delay=True,
            )
            file_formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback if log file cannot be created
            pass

    _loggers[name] = logger
    return logger

