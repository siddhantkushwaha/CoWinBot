# import time
#
# import telebot
# from db import dbHelper
#
# photo_pts = ['/Users/siddhantkushwaha/Downloads/mac.png']
#
# message = "If you want data for your area's pincode to be updated more frequently, " \
#           "you can do so by running a process on your system which updates bot's database more frequently. " \
#           "\nCheck above screenshot to see how it works. " \
#           "\n\nYou can download the process binary for Linux and Windows here https://cutt.ly/AbJbynB" \
#           "\n\nReport issues / ask questions at t.me/siddhantkushwaha"
#
# for i, user_info in enumerate(dbHelper.get_user_info_all(), 0):
#     user_id = user_info['userId']
#
#     if user_id in {1651414767, 1048804041, 863748044, 672187494, 1800920965, 1463112632, 939781702}:
#         continue
#
#     res = telebot.send_photo_url(user_id, message,
#                                  'AgACAgUAAxkDAAIdFWCdgmxXXQt9sx9hrH9Wj4mDPu-aAAIvrTEbpc_wVDrSOzh29K8PzzohbXQAAwEAAwIAA20AAxwiBgABHwQ')
#     print(user_id, res)
#
#     time.sleep(10)
