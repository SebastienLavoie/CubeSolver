from pathlib import Path
import datetime as dt
import logging
import logging.handlers


def setup(name="", suffix="", add_handler=False):
    LOGFILE = f'{name}{suffix}.log'
    logger = logging.getLogger(name)
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    if add_handler:
        formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")
        handler = logging.handlers.RotatingFileHandler(
            LOGFILE, maxBytes=(10*1024*1024), backupCount=7
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
