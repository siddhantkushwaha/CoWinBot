import time
from datetime import datetime
from functools import wraps

import requests
from telegram import (ChatAction, InlineKeyboardButton, InlineKeyboardMarkup,
                      ParseMode, ReplyKeyboardRemove, Update)
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

from customLogging import DATA, DEBUG, INFO, get_logger
from db import dbHelper
from fetcher import check_slot_get_response
from params import root_dir, tokens
from pincode_data import get_address_by_pincode, is_pincode_valid

logger = get_logger('telegram', path=root_dir, log_level=5)

token = tokens['cowinbot']

user_temp_data = {}



def send_typing_action(func):
                                                                                                 # Bot is typing
    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func




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

def send_messageMD2(user_id, message):
    send_text = f'https://api.telegram.org/bot{token}/sendMessage?chat_id={user_id}&parse_mode=MarkdownV2&text={message}'
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


    start_text = """Hi \!  This bot notifies you about the availability of slots for vaccination in your area\.

__List of Commands__ :\-\n\n
1 \- To start receiving notifications\,
          __click this__      \-\-\-\>       */request* \.\n
2 \- To stop receiving notifications\,
          __click this__      \-\-\-\>       */stop* \.\n
3 \- To list all your requests\,
          __click this__      \-\-\-\>       */list* \.\n
```
(You may also type these clickable commands instead\.)
```
\nReport issues at t\.me/siddhantkushwaha \."""

    second_text = """To check data for your pincode more frequently, you may run this program available on Google Drive on your PC.
Link - https://cutt.ly/AbJbynB .
\nThis will help the bot to update its database more frequently.\n(Refer to the attached screenshot.)"""

    screenshot_url = "https://github.com/siddhantkushwaha/siddhantkushwaha.github.io/raw/master/assets/img/screen.PNG"
    
    context.bot.send_message(parse_mode = ParseMode.MARKDOWN_V2,chat_id = user_id, text = start_text)    
    context.bot.send_photo(chat_id=user_id, caption=second_text, photo=screenshot_url)





# My Edits


AGE, REQUEST = 0 , 1

@send_typing_action
def request(update: Update, _: CallbackContext) -> int :

    # Conversation Started . Ask for Pincode.
     
    update.message.reply_text("Enter your Pincode")
    return AGE

@send_typing_action
def age(update: Update, _: CallbackContext) -> int :

    global user_temp_data
    user_id = update.effective_chat.id
    pincode = update.message.text

    if pincode == "/exit" :

        exit_message =  """Exited\!  To see all valid commands\,
click this   \-\-\-\>   */commands*"""

        send_messageMD2(user_id ,exit_message )                                                 # If user chose to exit
        return ConversationHandler.END    
          
    update_user_meta(user_id, update)

    log(user_id, INFO, f'Pincode [{pincode}] received.')

    if not pincode.isnumeric():
        response = """Incorrect pincode \!\n\nEnter it again, or __press__   \-\-\>   */exit*"""
        log(user_id, DEBUG, f'Pincode [{pincode}] is invalid.')
        update.message.reply_text(response,parse_mode = ParseMode.MARKDOWN_V2)  
        return AGE

    else:
        pincode = int(pincode)
        if not is_pincode_valid(pincode):
            response = f"Can\'t locate pincode\,\n\nEnter it again, or press   \-\-\>   */exit*"
            log(user_id, DEBUG, f'Cannot find pincode [{pincode}].')
            update.message.reply_text(response,parse_mode = ParseMode.MARKDOWN_V2)  
            return AGE
        else:
            time.sleep(1.2)
            response = f"Pincode found for area: {get_address_by_pincode(pincode)}."
            update.message.reply_text(response)
            
            user_temp_data["user_id"] = user_id 
            user_temp_data["pincode"] = pincode  
                                        
            button_list = [
            [InlineKeyboardButton("Above 45", callback_data="46"),
            InlineKeyboardButton("Below 45", callback_data="19")]]

            

            update.message.reply_text("Choose your age group:", reply_markup = InlineKeyboardMarkup(button_list))
            return REQUEST                                     #   exit this function
        
    update.message.reply_text(response)                                                           
    return ConversationHandler.END                                                           #   exit the ConversationHandler

@send_typing_action
def button_not_pressed(update: Update, _: CallbackContext) -> int :
    button_list = [
    [
    InlineKeyboardButton("Above 45", callback_data="46"),
    InlineKeyboardButton("Below 45", callback_data="19")
    ],
    [InlineKeyboardButton("Exit", callback_data="exit")]
    ]

    time.sleep(1.5)

    update.message.reply_text("Please click on one of these options !\nYou may also choose to exit. ", reply_markup = InlineKeyboardMarkup(button_list))
    return REQUEST                                   


@send_typing_action
def final(update: Update, _: CallbackContext) -> int :

    global user_temp_data
    query = update.callback_query
    age = query.data
    pincode = user_temp_data["pincode"]
    user_id = user_temp_data["user_id"]
 
    if age == "exit" :
        exit_message =  """Exited\!  To see all valid commands\,
click this   \-\-\-\>   */commands*"""
        send_messageMD2(user_id ,exit_message )                                     # If user chose to exit
        return ConversationHandler.END               


    ret = dbHelper.add_request(user_id, pincode, age)
    if ret > 1:
        response = 'Failed to register request, please try again.'
    elif ret == 1:
        response = 'You can only have 4 registered requests at a time.'
    else:
        log(user_id, INFO, f'Request registered.')
        response = f'Your request has been registered.\n' \
                    f'You will be notified when vaccine is available in area with ' \
                    f'pincode {pincode}.'

    # Sending two messages here, this is not good idea to do everywhere
    send_message(user_id , response)                                            

    pincode_info = dbHelper.get_pincode_info(pincode)
    response_type, response = check_slot_get_response(pincode_info, pincode, age)
    
    for res in response:
        send_message(user_id , response)                                                    
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
    
    return ConversationHandler.END 

@send_typing_action
def stop(update, context) :
    user_id = update.effective_chat.id
    user_requests = dbHelper.get_requests(user_id)
    if len(user_requests) > 0:
        ret = dbHelper.remove_all_requests(user_id)
        if ret > 0:
            response = 'Operation failed, please try again\.'
        else:
            response = 'You will not receive notifications\.'
    else:
        response = """You are not subscribed to notifications\.
To register\, click this   \-\-\-\>   */request*"""


    if type(response) == str and len(response) > 0:
        log(user_id, INFO, f'Final response sent.')
        log(user_id, DATA, response)
        context.bot.send_message(parse_mode = ParseMode.MARKDOWN_V2, chat_id=user_id, text=response)

@send_typing_action
def exit_request(update, context) :
    user_id = update.effective_chat.id
    response = """Exited\!
To see all valid commands\,
click this       \-\-\-\>       */commands*"""
    send_messageMD2(user_id , response) 


@send_typing_action
def list(update, context) :
    user_id = update.effective_chat.id
    user_requests = dbHelper.get_requests(user_id)
    if len(user_requests) > 0:
        response = "__List of your requests :\-__\n" 
        for i, val in enumerate(user_requests, 1):
            if val[1] == 46 :
                age =  '45\+'
            else :
                age = '18\+' 
            response += f"\n{i}\. Pincode : {val[0]}\,  Age : {age}"
            response = response.strip()
        response += """\n\nTo see all commands\,
click this   \-\-\-\>   */commands*"""  
    else:
        response = """You have no registered requests\.
To register\, click this   \-\-\-\>   */request*"""


    if type(response) == str and len(response) > 0:
        log(user_id, INFO, f'Final response sent.')
        log(user_id, DATA, response)
        context.bot.send_message(parse_mode = ParseMode.MARKDOWN_V2, chat_id=user_id, text=response)

@send_typing_action
def commands(update, context) :
    user_id = update.effective_chat.id

    command_text = """__List of Commands__ :\-\n\n
1 \- To start receiving notifications\,
          __click this__      \-\-\-\>       */request* \.\n
2 \- To stop receiving notifications\,
          __click this__      \-\-\-\>       */stop* \.\n
3 \- To list all your requests\,
          __click this__      \-\-\-\>       */list* \.\n
``` You may also type these clickable commands instead\.```
"""
    context.bot.send_message(parse_mode = ParseMode.MARKDOWN_V2,chat_id=user_id, text=command_text)

@send_typing_action
def invalid_command(update, context):
    user_id = update.effective_chat.id
    response = """Invalid command \!  To see all valid commands\,
click this   \-\-\-\>   */commands*"""
    context.bot.send_message(parse_mode = ParseMode.MARKDOWN_V2,chat_id=user_id, text = response)

"""
def show_more(update, context) :
    response = show_more                                # To be completed when /show more will be eanabled
    user_id = update.effective_chat.id
    x = dbHelper.get_user_info(user_id)
    print('not printed'*100,x, "printed" * 100)
"""


if __name__ == '__main__':

    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)                  # Start command
    dispatcher.add_handler(start_handler)

    #show_more_handler = CommandHandler('show', show_more)                  #show_more command Complete LATER
    #dispatcher.add_handler(show_more_handler)

    stop_handler = CommandHandler('stop', stop)                     # Stop command
    dispatcher.add_handler(stop_handler)

    list_handler = CommandHandler('list', list)                     # List requests
    dispatcher.add_handler(list_handler)

    command_list_handler = CommandHandler('commands',commands)                    
    dispatcher.add_handler(command_list_handler)




    # Conversation Handler


    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('request', request)],
        states={
            AGE : [MessageHandler(filters=Filters.text, callback = age, pass_user_data=True)],   
           REQUEST: [CallbackQueryHandler(final, pass_user_data=True)]
        },
        fallbacks=[MessageHandler(Filters.text & (~Filters.command), button_not_pressed),CommandHandler('exit', exit_request) ],
    )

    dispatcher.add_handler(conversation_handler)


    echo_handler = MessageHandler(Filters.text, invalid_command)
    dispatcher.add_handler(echo_handler)


    updater.start_polling()

    updater.idle()
    updater.stop()