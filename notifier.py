from datetime import datetime

import telebot
from customLogging import get_logger, INFO, DEBUG, DATA, WARNING
from db import dbHelper
from fetcher import check_slot_get_response
from params import root_dir
from util import get_key

logger = get_logger('notifier', path=root_dir, log_level=5)


def send_notification(
        user_id,
        pincode,
        age,

        # these two fields need to be as latest as possible, stale info could cause wrong/more notifications respectively
        pincode_info,
        user_info,

        min_time_diff_btw_pos=12 * 3600,
        min_time_diff_btw_neg=24 * 3600
):
    curr_time = datetime.utcnow()

    notification_state = get_key(user_info, ['notificationState', f'{pincode}_{age}'], {})

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
            logger.log(WARNING, '******** Impossible event, debug immediately. ********')
            return None, None

    elif notification_type == 'negative':
        logger.log(DEBUG, f'Slots NOT found for user [{user_id}], pincode [{pincode}], age [{age}].')
        message = f"No slots available in pincode area {pincode}, for {age} year olds."

    else:
        return None, None

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
                'timestamp': curr_time,
                'type': notification_type
            }
        })

        return notification_type, curr_time

    else:
        logger.log(INFO, f'Not notifying user [{user_id}].')
        return None, None
