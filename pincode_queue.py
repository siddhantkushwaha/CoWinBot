import json
import queue
import random
import time
from datetime import datetime
from threading import Thread

from flask import Flask, request

import aesutil
from customLogging import get_logger, INFO, DEBUG, WARNING
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

last_time_fetched_for_pincode = dict()
last_time_pinged_ip = dict()

logger = get_logger('pincode_queue', path=root_dir, log_level=5)


def is_string_json(string):
    try:
        json.loads(string)
        return True
    except:
        return False


def num_live_workers():
    """
        Returns an approximate number of workers running currently
    """

    curr_time = datetime.utcnow()
    for worker_ip, worker_ping_time in last_time_pinged_ip.items():
        time_diff = (curr_time - worker_ping_time).total_seconds()
        if time_diff > 300:
            last_time_pinged_ip.pop(worker_ip, None)
    return len(last_time_pinged_ip)


def get_from_queue():
    pincode = None
    try:
        pincode = process_queue.get(block=False)
    except queue.Empty as e:
        logger.log(INFO, 'Pincode queue empty, nothing to process.')
    except Exception as e:
        logger.exception(e)
    return pincode


def populate_process_queue(all_user_info):
    # clear process_queue
    pincode = get_from_queue()
    while pincode is not None:
        pincode = get_from_queue()

    # populate again
    pincodes = [i for i in get_all_pincodes(all_user_info)]
    random.shuffle(pincodes)

    for pincode in pincodes:
        process_queue.put(pincode)


def maintainer_thread():
    global user_requests_by_pincode, user_info_by_user_id

    i = 0
    while True:
        try:
            all_user_info = [i for i in dbHelper.get_user_info_all()]

            user_requests_by_pincode = build_user_requests_by_pincode(all_user_info)

            user_info_by_user_id = {i['userId']: i for i in all_user_info}

            # Every loop is about 5 minutes
            # 12 * 5 minutes = 1 hour
            if i % 12 == 0:
                populate_process_queue(all_user_info)

            num_workers = num_live_workers()
            logger.log(INFO, f"*********** Number of workers [{num_workers}] ***********")

            i += 1
        except Exception as e:
            logger.exception(e)

        # 5 minutes
        time.sleep(5 * 60)


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
    curr_time = datetime.utcnow()

    client_ip = request.remote_addr

    last_time_pinged_ip[client_ip] = curr_time

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
    curr_time = datetime.utcnow()

    data = request.form
    client_ip = request.remote_addr

    last_time_pinged_ip[client_ip] = curr_time

    pincode = int(data['pincode'])
    meta_encrypted = data['meta']

    key = f'{pincode}_{client_ip}'
    iv = f'{pincode}_{client_ip}'

    meta = None
    try:
        meta = aesutil.decrypt(meta_encrypted, key, iv)
        meta = meta.decode()
    except:
        meta = None

    if meta is None or len(meta) == 0:
        logger.log(WARNING, f'Unsafe/Invalid data sent for pincode [{pincode}] from ip [{client_ip}].')
        logger.log(DEBUG, meta)
        return {'error': 5}

    if not meta.startswith(f'{pincode}_'):
        logger.log(WARNING, f'Unsafe/Invalid data sent for pincode [{pincode}] from ip [{client_ip}].')
        logger.log(DEBUG, meta)
        return {'error': 5}

    meta = meta[7:]
    if not is_string_json(meta):
        logger.log(WARNING, f'Not JSON for pincode [{pincode}] from ip [{client_ip}].')
        logger.log(DEBUG, meta)
        return {'error': 5}

    # users who requested this pincode
    user_set = user_requests_by_pincode.get(pincode, set())

    if is_pincode_valid(pincode) and len(user_set) > 0:
        logger.log(INFO, f'Metadata received for pincode [{pincode}].')

        last_update_time = last_time_fetched_for_pincode.get(pincode, datetime.fromtimestamp(0))
        time_diff_seconds = (curr_time - last_update_time).total_seconds()

        if time_diff_seconds < 10:
            logger.log(INFO, f'Data was fetched very recently, {time_diff_seconds} seconds.')
            return {'error': 2}

        pincode_info = {
            'updateTimePeriod': time_diff_seconds,
            'modifiedTime': curr_time,
            'meta': meta,
        }

        dbHelper.get_or_create_pincode_info(pincode)
        ret = dbHelper.update_pincode_info_set(pincode, pincode_info)
        if ret == 0:
            logger.log(INFO, f'Data update success for [{pincode}].')
        else:
            logger.log(INFO, f'Failed to save to db.')
            return {'error': 1}

        last_time_fetched_for_pincode[pincode] = curr_time

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
    # starting maintainer thread
    th = Thread(name='maintainer_thread', target=maintainer_thread())
    th.start()

    app.run(host='0.0.0.0', port=5000)
