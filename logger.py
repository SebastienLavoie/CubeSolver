import logging
import logging.handlers


class Logger:
    def __init__(self):
        LOGFILE = f'solver.log'
        logger = logging.getLogger("")
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(filename)s - %(levelname)s - %(message)s")
        handler = logging.handlers.RotatingFileHandler(
            LOGFILE, maxBytes=(10*1024*1024), backupCount=7
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.logger = logger


logger = Logger().logger
logger.setLevel(logging.DEBUG)


def log(level, message):
    return logger.log(level, message)


def set_log_level(level):
    logger.setLevel(level)
