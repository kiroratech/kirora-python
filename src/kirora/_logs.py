from __future__ import annotations

import logging
import os

__all__ = ["logger", "configure_from_env"]

logger = logging.getLogger("kirora")

_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO}


def configure_from_env() -> None:
    """Logs to standard error if ``KIRORA_LOG`` is ``debug`` or ``info``."""
    level = _LEVELS.get(os.environ.get("KIRORA_LOG", "").strip().lower())
    if level is None or logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
