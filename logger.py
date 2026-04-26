import logging
import sys
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "tech_pulse.log")


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # pythonw.exe has no stdout — guard before adding console handler
    if sys.stdout is not None:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(fmt)
        logger.addHandler(console_handler)

    return logger


def add_gui_handler(handler: logging.Handler) -> None:
    """Attach handler to the root logger so all module loggers emit to it."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
    root.addHandler(handler)
