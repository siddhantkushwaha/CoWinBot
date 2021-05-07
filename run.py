import time

from fetcher import parse_pincode_age_requests, fetch
from notifier import send_notifications

if __name__ == '__main__':
    while True:
        all_user_req = parse_pincode_age_requests()

        fetch(all_user_req)
        send_notifications(all_user_req)

        # re-run every 3 hours
        time.sleep(3 * 3600)
