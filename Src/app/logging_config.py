import logging
import logging.handlers
from datetime import datetime

from Src.app.colors import *
from Src.app.config import app_config


def set_logger(log_name: str = 'app', console_level=logging.INFO):
    class ColorFormatter(logging.Formatter):
        LEVEL_COLORS = {
            logging.DEBUG: LIGHT_BLUE,
            logging.INFO: GREEN,
            logging.WARNING: YELLOW,
            logging.ERROR: LIGHT_RED,
            logging.CRITICAL: RED
        }

        def format(self, record):
            record.asctime = self.formatTime(record)

            time = f"{DARK_GRAY}{record.asctime}{WHITE}"
            # name = f"{MAGENTA}{record.name.ljust(8)}{WHITE}"
            level = f"{self.LEVEL_COLORS.get(record.levelno, DEFAULT)}{BOLD}{record.levelname}{RESET}{WHITE}"
            MESSAGE = f"{WHITE}{record.getMessage()}{WHITE}"
            filename = f"{DARK_GRAY}{record.filename}"
            funcname = f"{DARK_GRAY}{record.funcName}()"
            lineno = f"{DARK_GRAY}{record.lineno} line{RESET}"

            # format log message
            log_message = f"{time} - {level} |  {MESSAGE}  | {filename} · {funcname} · {lineno}"
            return log_message

        def formatTime(self, record, datefmt=None):
            log_time = datetime.fromtimestamp(record.created)
            if datefmt:
                return log_time.strftime(datefmt)
            return log_time.strftime('%H:%M:%S')

    app_logger = logging.getLogger(log_name)
    app_logger.setLevel(console_level)

    console_handler = logging.StreamHandler()
    color_formatter = ColorFormatter()
    console_handler.setFormatter(color_formatter)

    # Console handler
    console_handler.setLevel(console_level)
    app_logger.addHandler(console_handler)

    return logging.getLogger(log_name)


if app_config.DEBUG:
    logger = set_logger(console_level=logging.DEBUG)
else:
    logger = set_logger()
