import os
import time
from datetime import datetime

import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from customLogging import get_logger, INFO, DEBUG, DATA
from db import dbHelper
from fetcher import check_slot_get_response
from params import requests_dir, tokens
from util import load_request, save_request, delete_request, is_request_exists, load_pincode_set, load_pincode_dic, \
    load_notification_state, save_notification_state

logger = get_logger('telegram', log_level=5)

token = tokens['cowinbot']

pin_code_set = load_pincode_set()
pin_code_dic = load_pincode_dic()


def log(user_id, level, message):
    logger.log(level, f'{user_id} | {message}')


def update_user_meta(user_id, update):
    dbHelper.get_or_create_user_info(user_id)

    meta = {
        'username': update.message.chat.username,
        'first_name': update.message.chat.first_name,
        'last_name': update.message.chat.last_name
    }
    dbHelper.update_user_info(user_id, meta)


def send_message(user_id, message):
    send_text = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={user_id}&parse_mode=Markdown&text={message}'
    response = requests.get(send_text)
    return response.json()


def start(update, context):
    user_id = update.effective_chat.id
    update_user_meta(user_id, update)

    log(user_id, INFO, 'Start command received.')

    start_text = "Hi! This bot helps check if any slot is available for vaccination for given area, given age. " \
                 "\n\nTo get a notification as soon as slots are available, send command 'request <pin-code> <age>'. " \
                 "\n\nTo list all requests registered by you, send command 'list'. " \
                 "\n\nTo stop getting notifications, send command 'stop'." \
                 "\n\nReport issues at k16.siddhant@gmail.com"
    context.bot.send_message(chat_id=user_id, text=start_text)


def text_commands(update, context):
    user_id = update.effective_chat.id
    update_user_meta(user_id, update)

    command_text = update.message.text

    log(user_id, INFO, f'Text command [{command_text}] received.')

    user_request_path = os.path.join(requests_dir, f'{user_id}.json')

    command_text = command_text.strip().lower()
    command_args = command_text.split(' ')

    command_type = command_args[0] if len(command_args) > 0 else 'invalid'

    response = ''
    if command_type == 'request':
        if len(command_args) < 3:
            response = 'Invalid command. Use /start to see valid commands.'
        else:
            pincode = command_args[1]
            age = command_args[2]

            invalid_input = False

            if not pincode.isnumeric():
                invalid_input = True

            elif not age.isnumeric() or int(age) < 1 or int(age) > 110:
                invalid_input = True

            if invalid_input:
                response = 'Please check if pin-code and age provided are correct.'
                log(user_id, DEBUG, f'Pincode [{pincode}] or age [{age}] is invalid.')
            else:
                pincode = int(pincode)
                is_pincode_valid = pincode in pin_code_set
                if not is_pincode_valid:
                    response = f"Can't locate pincode, try again."
                    log(user_id, DEBUG, f'Cannot find pincode [{pincode}].')
                else:
                    pincode_info = pin_code_dic[pincode]
                    response = f"Pincode found for area: {pincode_info['Taluk']}, {pincode_info['divisionname']}, {pincode_info['circlename']}."
                    # Sending two messages here, this is not good idea to do everywhere
                    context.bot.send_message(chat_id=user_id, text=response)

                    user_request = load_request(user_request_path)

                    user_request_set = set(user_request.get('request', []))
                    user_request_set.add(f'{pincode}_{age}')

                    user_request['request'] = list(user_request_set)
                    save_request(user_request_path, user_request)

                    log(user_id, INFO, f'Request registered.')
                    response = f'Your request has been registered. ' \
                               f'You will be notified when vaccine is available in area with ' \
                               f'pincode {pincode} for {age} year olds.'

                    # Sending two messages here, this is not good idea to do everywhere
                    context.bot.send_message(chat_id=user_id, text=response)

                    response_type, response = check_slot_get_response(pincode, age)
                    for res in response:
                        context.bot.send_message(chat_id=user_id, text=res)
                        time.sleep(2)

                    # Updating notification state for this user so that, notifier module doesn't send
                    # notifications to this user immediately
                    log(user_id, DEBUG, f'Updating notification state, type [{response_type}]')
                    notification_state = load_notification_state(user_id)
                    notification_state_key = f'{pincode}_{age}'
                    notification_state[notification_state_key] = {
                        "timestamp": datetime.now(),
                        "type": response_type
                    }
                    save_notification_state(user_id, notification_state)

    elif command_type == 'stop':
        if is_request_exists(user_request_path):
            delete_request(user_request_path)
            response = 'You will not receive notifications.'
        else:
            response = 'You were not subscribed to notifications.'
    elif command_type == 'list':
        if is_request_exists(user_request_path):
            user_request = load_request(user_request_path)
            user_request_set = [i.split('_') for i in set(user_request.get('request', []))]
            user_request_tuple_set = [(i[0], i[1]) for i in user_request_set]
            response = ''
            for i, val in enumerate(user_request_tuple_set, 1):
                response += f"\n\n{i}. Pincode: {val[0]}, Age: {val[1]}"
            response = response.strip()
        else:
            response = 'You have no registered requests'
    else:
        response = 'Invalid command. Use /start to see valid commands.'

    if type(response) == str and len(response) > 0:
        log(user_id, INFO, f'Final response sent.')
        log(user_id, DATA, response)
        context.bot.send_message(chat_id=user_id, text=response)


if __name__ == '__main__':
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    echo_handler = MessageHandler(Filters.text & (~Filters.command), text_commands)
    dispatcher.add_handler(echo_handler)

    updater.start_polling()

    updater.idle()
    updater.stop()
