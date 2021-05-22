import logging
import os
from logging.handlers import RotatingFileHandler

logs_folder = 'logs'

DATA = 1
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR

pre_existing_loggers = {}


def get_logger(log_name, path='.', log_level=0):
    logger = pre_existing_loggers.get(log_name, None)
    if logger is None:
        logger = build_logger(log_name, path, log_level)
        pre_existing_loggers[log_name] = logger
    return logger


def build_logger(log_name, path, log_level):
    log_format = '%(lineno)10d %(asctime)s %(process)d %(thread)d %(module)20s %(funcName)30s %(levelname)8s | %(message)s'
    log_date_format = '%Y/%m/%d %H:%M:%S'

    logging.basicConfig(
        format=log_format,
        datefmt=log_date_format,
        level=log_level
    )

    logger = logging.getLogger(name=log_name)

    if log_name is not None:
        log_path = os.path.join(path, 'logs')
        os.makedirs(log_path, exist_ok=True)

        # 10 MB
        max_file_size = 10 * (2 ** 20)
        log_file_path_full = f'{os.path.join(log_path, log_name)}.log'

        rotating_file_handler = RotatingFileHandler(
            filename=log_file_path_full,
            mode='a',
            maxBytes=max_file_size,
            backupCount=5)
        rotating_file_handler.setFormatter(logging.Formatter(
            fmt=log_format,
            datefmt=log_date_format
        ))
        rotating_file_handler.setLevel(log_level)

        logger.addHandler(rotating_file_handler)

    return logger


if __name__ == '__main__':
    test_logger = get_logger('test')
    test_logger.log(DEBUG, 'Checking.')
