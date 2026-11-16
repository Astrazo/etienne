"""Send application and standard-library logs through one Loguru console sink."""

import inspect
import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """Forward standard logging records without losing their level or traceback."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Skip the logging machinery so Loguru reports the original caller.
        frame = inspect.currentframe()
        depth = 0
        while frame is not None:
            if depth > 0 and frame.f_code.co_filename != logging.__file__:
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def create_loguru_handler() -> InterceptHandler:
    """Configure the console in each Uvicorn process, including reload workers."""
    # Uvicorn reapplies dictConfig in spawned processes. Replacing the sink here
    # keeps configuration repeatable and avoids duplicate console output.
    logger.remove()
    logger.add(sys.stderr, level="INFO", backtrace=False, diagnose=False)
    return InterceptHandler()


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "loguru": {"()": "etienne.logging_config.create_loguru_handler"},
    },
    "root": {"handlers": ["loguru"], "level": "INFO"},
    "loggers": {
        # Remove Uvicorn's own handlers; each record goes to the root once.
        "uvicorn": {"handlers": [], "level": "INFO", "propagate": True},
        "uvicorn.error": {"handlers": [], "level": "INFO", "propagate": True},
        "uvicorn.access": {"handlers": [], "level": "INFO", "propagate": True},
        "fastapi": {"handlers": [], "level": "INFO", "propagate": True},
    },
}
