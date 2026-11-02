
import io
import logging
import logging.handlers as loghandler
import sys
import traceback as trb

from cubitools.commons.constants import CUBITOOLS_CONSTANTS as CT_CONST
from cubitools.commons.env import CUBITOOLS_ENVIRONMENT as CT_ENV


class CubiToolsLogger:

    def __init__(self, run_logger_name: str, debug: bool=False) -> None:
        """__init__ _summary_

        Args:
            run_logger_name (str): _description_
            debug (bool): _description_
            no_user_logger (bool): _description_
        """
        self.name = run_logger_name
        self.err_msg_no_user_logger = (
            "No user logger has been configured before calling "
            "the 'tell_user' or 'query_user' functions. This is "
            "a bug. Initialize a module-level logger other "
            "than 'main'."
        )
        self._init_run_logger(run_logger_name, debug)
        no_user_logger = run_logger_name == "main" or "STRUCTINIT" in run_logger_name
        if no_user_logger:
            self.user_logger = None
        else:
            self._init_user_logger()

        assert self.run_logger is not None
        if not no_user_logger:
            assert self.user_logger is not None

        return None

    def _init_run_logger(self, name: str, debug: bool) -> None:
        """The run logger must be used to record progress-type
        or error information. The logger uses two handlers,
        one for warning and up also send to stderr, and one
        file handler that represents the complete progress
        log, i.e. the file handler also captures INFO-level
        messages (see self.tell_user and self.query_user)

        Args:
            name (str): name of the logger, i.e. run-SUBCMD
            debug (bool): set level to debug for all handlers
        """
        stderr_console_formatter = logging.Formatter(
            fmt=CT_CONST.log_fmt_stderr,
            datefmt=CT_CONST.timestamp_format,
            style=CT_CONST.log_fmt_style
        )
        stderr_stream_handler = logging.StreamHandler(stream=sys.stderr)
        if debug:
            stderr_stream_handler.setLevel(logging.DEBUG)
        else:
            stderr_stream_handler.setLevel(logging.WARNING)
        stderr_stream_handler.setFormatter(stderr_console_formatter)

        file_formatter = logging.Formatter(
            fmt=CT_CONST.log_fmt_file,
            datefmt=CT_CONST.timestamp_format,
            style=CT_CONST.log_fmt_style
        )
        file_handler = loghandler.RotatingFileHandler(
            filename=CT_ENV.log_file,
            mode="a", delay=False,
            encoding=CT_CONST.default_text_encoding,
            maxBytes=524288, backupCount=2
        )
        if debug:
            file_handler.setLevel(logging.DEBUG)
        else:
            file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)

        self.run_logger = logging.getLogger(name)
        self.run_logger.setLevel(logging.DEBUG)
        self.run_logger.addHandler(stderr_stream_handler)
        self.run_logger.addHandler(file_handler)

        return None

    def _init_user_logger(self) -> None:
        """Initialize the logger that is used
        to interact with the user, i.e. that
        either sends INFO level progress messages
        or queries the user for input (typically,
        ask yes/no questions and return answer).
        """
        stdout_console_formatter = logging.Formatter(
            fmt=CT_CONST.log_fmt_stdout,
            datefmt=CT_CONST.timestamp_format,
            style=CT_CONST.log_fmt_style
        )
        stdout_stream_handler = logging.StreamHandler(stream=sys.stdout)
        stdout_stream_handler.setLevel(logging.INFO)
        stdout_stream_handler.setFormatter(stdout_console_formatter)

        if "user" in logging.root.manager.loggerDict:
            self.user_logger = logging.getLogger("user")
        else:
            self.user_logger = logging.getLogger("user")
            self.user_logger.setLevel(logging.INFO)
            self.user_logger.addHandler(stdout_stream_handler)

        return None

    def _system(self, msg: str, level: int) -> None:
        self.run_logger.log(level, msg)
        return None

    def set_debug_logging(self, debug: bool) -> None:

        if not debug:
            return None

        for handler in self.run_logger.handlers:
            handler.setLevel(logging.DEBUG)

        return None

    def tell_user(self, msg: str) -> None:
        if self.user_logger is None:
            raise RuntimeError(self.err_msg_no_user_logger)
        self.run_logger.info(msg)
        self.user_logger.info(msg)
        return None

    def query_user(self, msg: str) -> str:
        if self.user_logger is None:
            raise RuntimeError(self.err_msg_no_user_logger)
        self.run_logger.info(msg)
        user_input = input(msg).strip()
        record = f"user input: {user_input}"
        self.run_logger.info(record)
        return user_input

    def debug(self, msg: str) -> None:
        self._system(msg, logging.DEBUG)
        return None

    def info(self, msg: str) -> None:
        self._system(msg, logging.INFO)
        return None

    def warning(self, msg: str) -> None:
        self._system(msg, logging.WARNING)
        return None

    def error(self, msg: str) -> None:
        self._system(msg, logging.ERROR)
        return None

    def critical(self) -> None:
        trb_buffer = io.StringIO()
        trb.print_exc(file=trb_buffer)
        log_lines = []
        line_num = 0
        for line in trb_buffer.getvalue().split("\n"):
            if line.startswith("Traceback (most recent"):
                continue
            if not line.strip():
                continue
            if line.strip().startswith("^^^"):
                continue
            line_num += 1
            log_lines.append(
                f"[trbL:{line_num}] {line.strip()}"
            )
        log_lines = " /// ".join(log_lines) + "\n"
        self._system(log_lines, logging.CRITICAL)
        return None


class MockLogger:
    """Stand-in for a CubiToolsLogger that silently discards
    all logging events. Use as default for objects that may be
    created before a CubiToolsLogger is available, which avoids
    'if self.logger is not None' checks.
    """

    def __init__(self) -> None:
        """Initialize the mock logger; the name mimics the
        'name' attribute of a CubiToolsLogger.
        """
        self.name = "mock"
        self.err_msg_query_user = (
            "The MockLogger cannot query the user for input. This is "
            "a bug. Pass a CubiToolsLogger to the calling object."
        )
        return None

    def set_debug_logging(self, debug: bool) -> None:
        """Discard the request to activate debug logging.

        Args:
            debug (bool): ignored
        """
        return None

    def tell_user(self, msg: str) -> None:
        """Discard the message for the user.

        Args:
            msg (str): ignored
        """
        return None

    def query_user(self, msg: str) -> str:
        """Querying the user cannot be mocked because the caller
        expects an answer, which the MockLogger cannot provide.

        Args:
            msg (str): question for the user

        Raises:
            RuntimeError: always
        """
        raise RuntimeError(f"{self.err_msg_query_user} Query: {msg}")

    def debug(self, msg: str) -> None:
        """Discard the debug-level message.

        Args:
            msg (str): ignored
        """
        return None

    def info(self, msg: str) -> None:
        """Discard the info-level message.

        Args:
            msg (str): ignored
        """
        return None

    def warning(self, msg: str) -> None:
        """Discard the warning-level message.

        Args:
            msg (str): ignored
        """
        return None

    def error(self, msg: str) -> None:
        """Discard the error-level message.

        Args:
            msg (str): ignored
        """
        return None

    def critical(self) -> None:
        """Discard the traceback of the exception
        currently being handled.
        """
        return None


# Stateless, hence safe to share as default argument
MOCK_LOGGER = MockLogger()

