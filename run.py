import time

from customLogging import get_logger, INFO
from fetcher import parse_pincode_age_requests, fetch
from notifier import send_notifications

logger = get_logger('main', log_level=5)

if __name__ == '__main__':
    logger.log(INFO, '------------ Main program is now running ------------')

    while True:
        logger.log(INFO, '---------------- New iteration ----------------')

        all_user_req = parse_pincode_age_requests()

        fetch(
            all_user_req,
            min_time_diff_seconds=8 * 3600
        )

        send_notifications(
            all_user_req,
            min_time_diff_btw_pos=12 * 3600,
            min_time_diff_btw_neg=24 * 3600
        )

        # re-run every 5 minutes
        time.sleep(5 * 60)
