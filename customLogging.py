import os

import logging
from logging.handlers import RotatingFileHandler

logs_folder = 'logs'

DATA = 1
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR


def get_logger(log_name=None, path='.', log_level=0):
    log_format = '%(lineno)d %(asctime)s %(module)s %(funcName)s %(levelname)8s | %(message)s'
    log_date_format = '%Y/%m/%d %H:%M:%S'

    logging.basicConfig(
        format=log_format,
        datefmt=log_date_format,
        level=log_level
    )

    logger = logging.getLogger()

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
    logger = get_logger('test')
    logger.log(DEBUG, 'Checking.')
