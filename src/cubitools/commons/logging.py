
import logging
import logging.handlers as loghandler
import sys

from cubitools.commons.constants import RUNTIME_CONSTANTS
from cubitools.commons import CT_ENV


def get_run_logger(logger_name, debug):

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    console_formatter = logging.Formatter(
        fmt="{asctime} - {levelname} - {filename} - L:{lineno}: {message}",
        datefmt=RUNTIME_CONSTANTS.timestamp_format,
        style="{"
    )
    console_handler = logging.StreamHandler(stream=sys.stderr)
    if debug:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter)

    file_formatter = logging.Formatter(
        fmt="{asctime}\t{levelname}\t{filename}\tL:{lineno}\t{message}",
        datefmt=RUNTIME_CONSTANTS.timestamp_format,
        style="{"
    )
    file_handler = loghandler.RotatingFileHandler(
        filename=CT_ENV.log_file,
        mode="a", delay=False,
        encoding=RUNTIME_CONSTANTS.file_encoding,
        maxBytes=524288, backupCount=2
    )
    if debug:
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
