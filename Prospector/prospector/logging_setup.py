"""Logging con color en consola y traza completa en disco."""
from __future__ import annotations

import logging
import sys
from datetime import date

from .config import LOGS_DIR

_COLORS = {
    "DEBUG": "\033[38;5;244m",
    "INFO": "\033[38;5;39m",
    "WARNING": "\033[38;5;214m",
    "ERROR": "\033[38;5;196m",
    "CRITICAL": "\033[48;5;196m\033[97m",
}
_RESET = "\033[0m"
_ICONS = {"DEBUG": "·", "INFO": "→", "WARNING": "!", "ERROR": "✗", "CRITICAL": "☠"}


class _ConsoleFormatter(logging.Formatter):
    def __init__(self, color: bool) -> None:
        super().__init__("%(message)s")
        self.color = color

    def format(self, record: logging.LogRecord) -> str:
        icon = _ICONS.get(record.levelname, "·")
        msg = record.getMessage()
        if record.exc_info:
            msg = f"{msg}\n{self.formatException(record.exc_info)}"
        if not self.color:
            return f"[{icon}] {msg}"
        color = _COLORS.get(record.levelname, "")
        return f"{color}[{icon}]{_RESET} {msg}"


def setup_logging(verbose: bool = False, name: str = "prospector") -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    color = getattr(sys.stdout, "isatty", lambda: False)() and sys.platform != "emscripten"
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(_ConsoleFormatter(color))
    logger.addHandler(console)

    file_handler = logging.FileHandler(
        LOGS_DIR / f"prospector-{date.today():%Y-%m-%d}.log", encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )
    logger.addHandler(file_handler)

    # Silenciar el ruido de librerías de terceros.
    for noisy in ("asyncio", "urllib3", "httpx", "google_genai", "playwright"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger


def get_logger(suffix: str = "") -> logging.Logger:
    base = setup_logging()
    return base.getChild(suffix) if suffix else base
