import time
from datetime import datetime

import requests
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from customLogging import get_logger, INFO, DEBUG, DATA
from db import dbHelper
from fetcher import check_slot_get_response
from params import tokens, root_dir
from pincode_data import is_pincode_valid, get_address_by_pincode

logger = get_logger('telegram', path=root_dir, log_level=5)

token = tokens['cowinbot']


def log(user_id, level, message):
    logger.log(level, f'{user_id} | {message}')


def update_user_meta(user_id, update):
    dbHelper.get_or_create_user_info(user_id)

    meta = {
        'username': update.message.chat.username,
        'first_name': update.message.chat.first_name,
        'last_name': update.message.chat.last_name
    }
    dbHelper.update_user_info_set(user_id, meta)


def send_message(user_id, message):
    send_text = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={user_id}&parse_mode=Markdown&text={message}'
    response = requests.get(send_text)
    return response.json()


def send_photo_url(user_id, text, url):
    params = {
        'chat_id': user_id,
        'photo': url,
        'caption': text
    }
    response = requests.post(f'https://api.telegram.org/bot{token}/sendPhoto', params)
    return response.json()


def send_photo_file_pt(user_id, text, file):
    file = open(file, 'rb')

    params = {
        'chat_id': user_id,
        'caption': text
    }

    files = {
        'photo': file
    }

    response = requests.post(f'https://api.telegram.org/bot{token}/sendPhoto', params, files=files)

    file.close()

    return response.json()


def send_photo_file(user_id, text, file):
    params = {
        'chat_id': user_id,
        'caption': text
    }

    files = {
        'photo': file
    }

    response = requests.post(f'https://api.telegram.org/bot{token}/sendPhoto', params, files=files)

    return response.json()


def start(update, context):
    user_id = update.effective_chat.id
    update_user_meta(user_id, update)

    log(user_id, INFO, 'Start command received.')

    start_text = "Hi! This bot helps check if any slot is available for vaccination for given area, given age. " \
                 "\n\nTo get a notification as soon as slots are available, send command 'request <pin-code> <age>'. " \
                 "\n\nTo list all requests registered by you, send command 'list'. " \
                 "\n\nTo stop getting notifications, send command 'stop'." \
                 "\n\nReport issues at t.me/siddhantkushwaha"

    context.bot.send_message(chat_id=user_id, text=start_text)

    # Let's see how many decide to help.
    second_text = "Data for your pincode may not be getting checked as frequently as you'd like." \
                  "\n\nYou can help update bot's database more frequently by running a process available on Google Drive here https://cutt.ly/AbJbynB" \
                  "\n\nCheck attached screenshot to learn how you can help."
    screenshot_url = "https://github.com/siddhantkushwaha/siddhantkushwaha.github.io/raw/master/assets/img/screen.PNG"

    context.bot.send_photo(chat_id=user_id, caption=second_text, photo=screenshot_url)


def text_commands(update, context):
    user_id = update.effective_chat.id
    update_user_meta(user_id, update)

    command_text = update.message.text

    log(user_id, INFO, f'Text command [{command_text}] received.')

    command_text = command_text.strip().lower()
    command_args = command_text.split(' ')

    command_type = command_args[0] if len(command_args) > 0 else 'invalid'

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
                if not is_pincode_valid(pincode):
                    response = f"Can't locate pincode, try again."
                    log(user_id, DEBUG, f'Cannot find pincode [{pincode}].')
                else:

                    response = f"Pincode found for area: {get_address_by_pincode(pincode)}."

                    # Sending two messages here, this is not good idea to do everywhere
                    context.bot.send_message(chat_id=user_id, text=response)

                    ret = dbHelper.add_request(user_id, pincode, age)
                    if ret > 1:
                        response = 'Failed to register request, please try again.'
                    elif ret == 1:
                        response = 'You can only have 4 registered requests at a time.'
                    else:
                        log(user_id, INFO, f'Request registered.')
                        response = f'Your request has been registered. ' \
                                   f'You will be notified when vaccine is available in area with ' \
                                   f'pincode {pincode} for {age} year olds.'

                    # Sending two messages here, this is not good idea to do everywhere
                    context.bot.send_message(chat_id=user_id, text=response)

                    pincode_info = dbHelper.get_pincode_info(pincode)
                    response_type, response = check_slot_get_response(pincode_info, pincode, age)
                    for res in response:
                        context.bot.send_message(chat_id=user_id, text=res)
                        time.sleep(2)

                    # Updating notification state for this user so that notifier module doesn't send
                    # notifications to this user immediately
                    log(user_id, DEBUG, f'Updating notification state, type [{response_type}]')
                    dbHelper.update_user_info_set(user_id, {
                        f'notificationState.{pincode}_{age}': {
                            'timestamp': datetime.utcnow(),
                            'type': response_type
                        }
                    })

    elif command_type == 'stop':
        user_requests = dbHelper.get_requests(user_id)
        if len(user_requests) > 0:
            ret = dbHelper.remove_all_requests(user_id)
            if ret > 0:
                response = 'Operation failed, please try again.'
            else:
                response = 'You will not receive notifications.'
        else:
            response = 'You are not subscribed to notifications.'

    elif command_type == 'list':
        user_requests = dbHelper.get_requests(user_id)
        if len(user_requests) > 0:
            response = ''
            for i, val in enumerate(user_requests, 1):
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
