import time
from datetime import datetime

import telebot
from customLogging import get_logger, INFO, DEBUG, DATA
from fetcher import check_slots_available
from util import load_pincode_set, load_notification_state, save_notification_state

logger = get_logger('notifier', log_level=5)

valid_pincode_set = load_pincode_set()


def send_notifications(all_req, min_time_diff_btw_pos, min_time_diff_btw_neg):
    logger.log(INFO, '-------------- Initiating sending notifications --------------')

    curr_time = datetime.now()

    for user_id, req in all_req.items():
        for i in req:
            notification_state = load_notification_state(user_id)

            pincode = int(i[0])
            age = int(i[1])

            if pincode not in valid_pincode_set:
                continue

            timestamp, response = check_slots_available(pincode, age)
            if response is not None and len(response) > 0:
                logger.log(DEBUG, f'Slots found for user [{user_id}], pincode [{pincode}], age [{age}].')
                logger.log(DATA, response)

                notification_type = 'positive'
                message = f"You have slots available in pincode area {pincode}, for {age} year olds, use command 'request {pincode} {age} to check centers.'"

            elif response is not None:
                logger.log(DEBUG, f'Slots NOT found for user [{user_id}], pincode [{pincode}], age [{age}].')

                notification_type = 'negative'
                message = f"No slots available in pincode area {pincode}, for {age} year olds."

            else:
                continue

            notify = False
            notification_state_key = f'{pincode}_{age}'
            if len(notification_state.get(notification_state_key, {})) > 0:
                last_time_sent = notification_state[notification_state_key]['timestamp']
                last_notification_type = notification_state[notification_state_key]['type']
                time_diff_seconds = (curr_time - last_time_sent).total_seconds()

                logger.log(DEBUG, f'Found notification state for user [{user_id}], '
                                  f'last time sent [{last_time_sent}], '
                                  f'last notification type [{last_notification_type}], '
                                  f'current notification type [{notification_type}], time difference in seconds [{time_diff_seconds}].')

                if last_notification_type == 'negative' and notification_type == 'positive':
                    notify = True
                elif last_notification_type == 'negative' and notification_type == 'negative':
                    # send negative notifications repeatedly not closer than 24 hours
                    if time_diff_seconds > min_time_diff_btw_neg:
                        notify = True
                elif last_notification_type == 'positive' and notification_type == 'negative':
                    notify = True
                elif last_notification_type == 'positive' and notification_type == 'positive':
                    # send positive notifications repeatedly not closer than 6 hours
                    if time_diff_seconds > min_time_diff_btw_pos:
                        notify = True
                else:
                    notify = True
            else:
                notify = True

            if notify:
                logger.log(INFO, f'Notifying user [{user_id}], message [{message}].')

                telebot.send_message(user_id, message)
                notification_state[notification_state_key] = {
                    "timestamp": curr_time,
                    "type": notification_type
                }
                save_notification_state(user_id, notification_state)

                time.sleep(5)
            else:
                logger.log(INFO, f'Not notifying user [{user_id}].')
