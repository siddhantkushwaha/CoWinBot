# import time
#
# import telebot
# from db import dbHelper
#
# second_text = "Data for your pincode may not be getting checked as frequently as you'd like." \
#               "\n\nYou can help update bot's database more frequently by running a process available on Google Drive here https://cutt.ly/AbJbynB" \
#               "\n\nCheck attached screenshot to learn how you can help."
# screenshot_url = "https://github.com/siddhantkushwaha/siddhantkushwaha.github.io/raw/master/assets/img/screen.PNG"
#
# for i, user_info in enumerate(dbHelper.get_user_info_all(), 0):
#     user_id = user_info['userId']
#
#     res = telebot.send_photo_url(user_id, second_text, screenshot_url)
#     print(user_id, res)
#
#     time.sleep(2)
