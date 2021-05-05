import time

import telebot
from fetcher import fetch, parse_requests, check_slots_available


def send_notifications(all_req, notify=False):
    for user_id, req in all_req.items():
        for i in req:
            timestamp, response = check_slots_available(i[0], i[1])
            if response is not None and len(response) > 0:

                print(f'Qualified response: {response}')

                if notify:
                    print(f'Notifying user: {user_id}')

                    message = f"You have slots available in pincode area {i[0]}, for {i[1]} year olds, use command 'request {i[0]} {i[1]} to check.'"
                    telebot.send_message(user_id, message)
                    time.sleep(1)


def run(i):
    all_req = parse_requests()

    if i > 0:
        print('Fetching results.')
        fetch(all_req)

    send_notifications(all_req, i > 0)


if __name__ == '__main__':

    i = 0
    while True:
        run(i)
        i += 1

        # re-run every 3 hours
        time.sleep(3 * 3600)
