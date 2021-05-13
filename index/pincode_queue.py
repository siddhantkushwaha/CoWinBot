import queue
import time
from threading import Thread

from flask import Flask, request

from customLogging import get_logger, INFO, DEBUG
from db import dbHelper
from fetcher import get_all_pincodes
from params import root_dir
from util import load_pincode_set

app = Flask(__name__)

process_queue = queue.Queue()
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
    pincodes = get_all_pincodes(all_user_info)
    for pincode in pincodes:
        process_queue.put(pincode)


def worker_thread_func():
    while True:
        populate_process_queue()

        # 1 hour
        time.sleep(1 * 60 * 60)


def init_worker_thread():
    th = Thread(name='cowin_pincode_queue_worker', target=worker_thread_func)
    th.start()


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

        return {'error': 0, 'message': 'Pincode data capture success.'}
    else:
        logger.log(INFO, f'Invalid pincode [{pincode}]. Something wrong with worker code?')

        return {'error': 1, 'message': 'Invalid pincode.'}


if __name__ == '__main__':
    init_worker_thread()

    app.run(host='0.0.0.0', port=5000)
