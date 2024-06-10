"""
The main logger to be used by the program.
"""

import logging
import os

main_logger: logging.Logger = logging.getLogger("runner")

if not os.path.exists("logs"):
    os.makedirs("logs")

# Allow all log levels
main_logger.setLevel(logging.DEBUG)


def setup():
    """
    Setup the logger.
    """
    global main_logger

    formatter_c = logging.Formatter(
        "%(asctime)s  [\033[93m%(pathname)s:%(lineno)d\033[0m]  %(levelname)s: %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter_c)
    main_logger.addHandler(console_handler)


setup()
