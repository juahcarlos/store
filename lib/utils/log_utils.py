import logging
import sys
import warnings
from logging import DEBUG, Formatter, Handler, LogRecord, StreamHandler, captureWarnings


class ColorFormatter(Formatter):
    """Logging formatter adding console colors to the output. Taken from
    https://github.com/qtile/qtile/blob/842038e2048ad0f56fed40efaf45b43a9a3fb883/libqtile/log_utils.py#L42
    """

    black, red, green, yellow, blue, magenta, cyan, white = range(8)
    colors = {
        "WARNING": yellow,
        "INFO": green,
        "DEBUG": blue,
        "CRITICAL": yellow,
        "ERROR": red,
        "RED": red,
        "GREEN": green,
        "YELLOW": yellow,
        "BLUE": blue,
        "MAGENTA": magenta,
        "CYAN": cyan,
        "WHITE": white,
    }
    reset_seq = "\033[0m"
    color_seq = "\033[%dm"
    bold_seq = "\033[1m"

    def format(self, record: LogRecord) -> str:
        """Format the record with colors."""
        color = self.color_seq % (30 + self.colors[record.levelname])
        message = Formatter.format(self, record)
        message = message.replace("$RESET", self.reset_seq).replace("$BOLD", self.bold_seq).replace("$COLOR", color)
        for color, value in self.colors.items():
            message = (
                message.replace("$" + color, self.color_seq % (value + 30))
                .replace("$BG" + color, self.color_seq % (value + 40))
                .replace("$BG-" + color, self.color_seq % (value + 40))
            )
        return message + self.reset_seq


def init_logging(package_name: str, verbosity: int = DEBUG, debug_handler: Handler = None) -> None:
    logger_package = logging.getLogger(package_name)
    logger_bluelib = logging.getLogger("bluelib")
    for handler in logger_package.handlers:
        logger_package.removeHandler(handler)
    for handler in logger_bluelib.handlers:
        logger_bluelib.removeHandler(handler)

    if debug_handler:
        handler = debug_handler
    else:
        handler = StreamHandler(sys.stdout)
    formatter: Formatter = ColorFormatter(
        "$RESET$COLOR%(asctime)s %(levelname)s: $BOLD$COLOR%(name)s"
        " %(filename)s:%(funcName)s():L%(lineno)d $RESET %(message)s"
    )
    handler.setFormatter(formatter)
    logger_package.addHandler(handler)
    logger_bluelib.addHandler(handler)
    logger_package.setLevel(verbosity)
    logger_bluelib.setLevel(verbosity)
    captureWarnings(True)
    warnings.simplefilter("always")
    logger_bluelib.debug("started logging")
    logger_package.debug("started logging")
