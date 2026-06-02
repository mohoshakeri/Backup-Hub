import logging
import sys


def configure_logging() -> None:
    root_logger: logging.Logger = logging.getLogger()

    if root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        return

    handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
