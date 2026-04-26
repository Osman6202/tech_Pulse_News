import os
import sys

# MUST be first — startup shortcut may not preserve working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from config import validate_config
from logger import get_logger
from gui import MainWindow

logger = get_logger(__name__)


def main() -> None:
    warnings = validate_config()
    for w in warnings:
        logger.warning(w)

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
