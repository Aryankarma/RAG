"""Configure logging for `app.*` loggers (does not strip uvicorn's root handlers)."""

import logging
import os
import sys


def setup_logging() -> None:
    level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    app_log = logging.getLogger("app")
    app_log.setLevel(level)

    # Avoid duplicate lines if setup_logging runs twice (e.g. reload)
    if not any(
        isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
        for h in app_log.handlers
    ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        app_log.addHandler(handler)

    # Do not duplicate these lines on the root logger (uvicorn also uses root).
    app_log.propagate = False

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
