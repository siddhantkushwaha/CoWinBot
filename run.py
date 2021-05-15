import time

from customLogging import get_logger, INFO
from db import dbHelper
from fetcher import fetch
from notifier import send_notifications
from params import root_dir

logger = get_logger('main', path=root_dir, log_level=5)

if __name__ == '__main__':
    logger.log(INFO, '------------ Main program is now running ------------')

    while True:
        logger.log(INFO, '---------------- New iteration ----------------')

        all_user_info = [i for i in dbHelper.get_user_info_all()]

        fetch(
            all_user_info,
            min_time_diff_seconds=5 * 3600
        )

        send_notifications(
            all_user_info,
            min_time_diff_btw_pos=12 * 3600,
            min_time_diff_btw_neg=24 * 3600
        )

        # re-run every 30 minutes
        time.sleep(30 * 60)
