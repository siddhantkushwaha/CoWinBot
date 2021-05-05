import time

import telebot
from fetcher import fetch, parse_requests, check_slots_available


def send_notifications(all_req):
    for user_id, req in all_req.items():
        for i in req:
            timestamp, response = check_slots_available(i[0], i[1])
            if response is not None and len(response) > 0:
                message = f"You have slots available in pincode area {i[0]}, for {i[1]} year olds, use command 'request {i[0]} {i[1]} to check.'"
                telebot.send_message(user_id, message)


def run(notify=False):
    all_req = parse_requests()

    print('Fetching..')
    fetch(all_req)

    if notify:
        print('Notifying..')
        send_notifications(all_req)


if __name__ == '__main__':

    is_notify = False
    while True:
        run(is_notify)
        is_notify = True

        # re-run every 3 hours
        time.sleep(3 * 3600)
