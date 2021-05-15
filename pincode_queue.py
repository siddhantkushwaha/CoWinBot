import queue
import time
import random
from datetime import datetime
from threading import Thread

from flask import Flask, request

from customLogging import get_logger, INFO, DEBUG
from db import dbHelper
from fetcher import get_all_pincodes, build_user_requests_by_pincode
from notifier import send_notification
from params import root_dir
from util import load_pincode_set, set_key

app = Flask(__name__)

process_queue = queue.Queue()
user_requests_by_pincode = dict()
user_info_by_user_id = dict()

valid_pincodes = load_pincode_set()

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


def send_notifications_thread(pincode, pincode_meta):
    by_pincode = user_requests_by_pincode.get(pincode, set())
    if len(by_pincode) > 0:

        # create info obj instead of fetching from db
        pincode_info = {
            'modifiedTime': datetime.utcnow(),
            'meta': pincode_meta
        }

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
                # TODO experimental time gap decrease
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

    if pincode in valid_pincodes:
        logger.log(INFO, f'Metadata received for pincode [{pincode}].')
        logger.log(DEBUG, meta)

        ret = dbHelper.update_pincode_info_set(pincode, {'meta': meta})
        if ret == 0:
            logger.log(INFO, f'Data update success for [{pincode}].')
        else:
            logger.log(INFO, f'Failed to save to db.')

        notification_th = Thread(target=send_notifications_thread, args=[pincode, meta])
        notification_th.start()

        return {'error': 0}
    else:
        logger.log(INFO, f'Invalid pincode [{pincode}]. Something wrong with worker code?')

        return {'error': 1}


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
