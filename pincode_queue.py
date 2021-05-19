import queue
import random
import time
from datetime import datetime
from threading import Thread

from flask import Flask, request

from customLogging import get_logger, INFO, DEBUG
from db import dbHelper
from fetcher import get_all_pincodes, build_user_requests_by_pincode
from notifier import send_notification
from params import root_dir
from pincode_data import is_pincode_valid
from util import set_key

app = Flask(__name__)

process_queue = queue.Queue()
user_requests_by_pincode = dict()
user_info_by_user_id = dict()

last_time_fetched = dict()

logger = get_logger('pincode_queue', path=root_dir, log_level=5)


def get_from_queue():
    pincode = None
    try:
        pincode = process_queue.get(block=False)
    except queue.Empty as e:
        logger.log(INFO, 'Pincode queue empty, nothing to process.')
    except Exception as e:
        logger.exception(e)
    return pincode


def populate_process_queue():
    # clear process_queue
    pincode = get_from_queue()
    while pincode is not None:
        pincode = get_from_queue()

    # populate again
    all_user_info = dbHelper.get_user_info_all()

    pincodes = [i for i in get_all_pincodes(all_user_info)]
    random.shuffle(pincodes)

    for pincode in pincodes:
        process_queue.put(pincode)


def worker_thread_func():
    while True:
        populate_process_queue()

        # 1 hour
        time.sleep(1 * 60 * 60)


def worker_refresh_user_requests_by_pincode():
    global user_requests_by_pincode, user_info_by_user_id

    while True:
        all_user_info = [i for i in dbHelper.get_user_info_all()]

        user_requests_by_pincode = build_user_requests_by_pincode(all_user_info)
        user_info_by_user_id = {i['userId']: i for i in all_user_info}

        # 5 minutes
        time.sleep(5 * 60)


def init_worker_thread(name, target):
    th = Thread(name=name, target=target)
    th.start()


def send_notifications_thread(pincode, pincode_info):
    by_pincode = user_requests_by_pincode.get(pincode, set())
    if len(by_pincode) > 0:
        for user_id, age in by_pincode:

            # user_info dic is updated every 5 minutes by another thread
            user_info = user_info_by_user_id.get(user_id, None)
            if user_info is None:
                logger.log(DEBUG, '******** Impossible event, debug immediately. ********')
                continue

            notification_type, send_time = send_notification(user_id, pincode, age, pincode_info, user_info)
            if send_time is not None:
                # update cached object
                set_key(user_info, ['notificationState', f'{pincode}_{age}'], {
                    'timestamp': send_time,
                    'type': notification_type
                })

                # wait if message was sent, to ease on telegram api
                # notifications are sent in short bursts (experimental)
                time.sleep(0.5)


@app.route('/get', methods=['GET'])
def get_pincode():
    """
        returns a pincode for the worker node to process
    """
    pincode = get_from_queue()
    if pincode is not None:
        logger.log(DEBUG, f'Moving [{pincode}] to end of queue.')
        process_queue.put(pincode)

    return {'pincode': pincode}


@app.route('/index', methods=['POST'])
def index_pincode():
    """
        indexes a pin-code's info returned by worker nodes
    """
    data = request.form
    pincode = int(data['pincode'])
    meta = data['meta']

    # users who requested this pincode
    user_set = user_requests_by_pincode.get(pincode, set())

    if is_pincode_valid(pincode) and len(user_set) > 0:
        logger.log(INFO, f'Metadata received for pincode [{pincode}].')
        logger.log(DEBUG, meta)

        curr_time = datetime.utcnow()
        last_update_time = last_time_fetched.get(pincode, datetime.fromtimestamp(0))
        time_diff_seconds = (curr_time - last_update_time).total_seconds()

        if time_diff_seconds < 10:
            logger.log(INFO, f'Data was fetched very recently, {time_diff_seconds} seconds.')
            return {'error': 2}

        pincode_info = {
            'modifiedTime': curr_time,
            'meta': meta
        }

        dbHelper.get_or_create_pincode_info(pincode)
        ret = dbHelper.update_pincode_info_set(pincode, pincode_info)
        if ret == 0:
            logger.log(INFO, f'Data update success for [{pincode}].')
        else:
            logger.log(INFO, f'Failed to save to db.')
            return {'error': 1}

        last_time_fetched[pincode] = curr_time

        notification_th = Thread(target=send_notifications_thread, args=[pincode, pincode_info])
        notification_th.start()

        return {'error': 0}

    elif is_pincode_valid(pincode):
        logger.log(INFO, f'No user requested for [{pincode}].')
        return {'error': 4}

    else:
        logger.log(INFO, f'Invalid pincode [{pincode}].')
        return {'error': 3}


if __name__ == '__main__':
    init_worker_thread(
        name='cowin_pincode_queue_worker',
        target=worker_thread_func
    )

    init_worker_thread(
        name='cowin_requests_by_pincode_worker',
        target=worker_refresh_user_requests_by_pincode
    )

    app.run(host='0.0.0.0', port=5000)
