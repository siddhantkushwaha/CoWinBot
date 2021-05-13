import time
from datetime import datetime

import telebot
from customLogging import get_logger, INFO, DEBUG, DATA
from db import dbHelper
from fetcher import check_slot_get_response
from params import root_dir
from util import load_pincode_set, get_key

logger = get_logger('notifier', path=root_dir, log_level=5)

valid_pincode_set = load_pincode_set()


def send_notifications(all_user_info, min_time_diff_btw_pos, min_time_diff_btw_neg):
    logger.log(INFO, '-------------- Initiating sending notifications --------------')

    all_pincode_info_dic = {i['pincode']: i for i in dbHelper.get_pincode_info_all()}

    for user_info in all_user_info:
        user_id = user_info['userId']
        user_request = dbHelper.get_requests_userinfo(user_info)

        for pincode, age in user_request:
            curr_time = datetime.utcnow()

            pincode_info = all_pincode_info_dic.get(pincode, None)
            notification_state = get_key(user_info, ['notificationState', f'{pincode}_{age}'], {})

            if pincode not in valid_pincode_set:
                continue

            notification_type, response = check_slot_get_response(pincode_info, pincode, age)

            if notification_type == 'positive':
                logger.log(DEBUG, f'Slots found for user [{user_id}], pincode [{pincode}], age [{age}].')
                logger.log(DATA, response)

                if len(response) > 1:
                    message = f"You have slots available in pincode area {pincode}, for {age} year olds, use command 'request {pincode} {age}' to check centers."
                elif len(response) > 0:
                    message = f"You have slots available in pincode area {pincode}, for {age} year olds." \
                              f"\n\n{response[0]}"
                else:
                    logger.exception('*********** Impossible condition, check immediately. ***********')
                    continue

            elif notification_type == 'negative':
                logger.log(DEBUG, f'Slots NOT found for user [{user_id}], pincode [{pincode}], age [{age}].')

                message = f"No slots available in pincode area {pincode}, for {age} year olds."

            else:
                continue

            notify = False

            if len(notification_state) > 0:
                last_time_sent = notification_state['timestamp']
                last_notification_type = notification_state['type']
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

                dbHelper.update_user_info_set(user_id, {
                    f'notificationState.{pincode}_{age}': {
                        'timestamp': datetime.utcnow(),
                        'type': notification_type
                    }
                })

                time.sleep(5)
            else:
                logger.log(INFO, f'Not notifying user [{user_id}].')
