from datetime import datetime

from customLogging import get_logger, INFO
from db.database import Database
from params import config, root_dir
from util import get_key

db = Database()

logger = get_logger(log_name='db', path=root_dir, log_level=5)


def get_user_info(user_id):
    user_id = int(user_id)

    data = db.userInfo.find_one({'userId': user_id})
    return data


def get_user_info_all():
    data = db.userInfo.find()
    return data


def update_user_info_set(user_id, user_info):
    user_id = int(user_id)

    try:
        user_info['modifiedTime'] = datetime.utcnow()
        db.userInfo.update_one({'userId': user_id}, update={'$set': user_info})
        return 0
    except Exception as e:
        logger.exception(e)
        return 1


def create_user_info(user_id):
    user_id = int(user_id)

    try:
        data = {'userId': user_id}
        db.userInfo.insert_one(document=data)
        return data
    except Exception as e:
        logger.exception(e)
        return None


def get_or_create_user_info(user_id):
    user_id = int(user_id)

    data = get_user_info(user_id)
    if data is None:
        data = create_user_info(user_id)
    return data


def get_requests(user_id):
    user_id = int(user_id)

    user_info = get_user_info(user_id)
    requests = get_key(user_info, ['requests'], [])
    return set([(request[0], request[1]) for request in requests])


def get_requests_userinfo(user_info):
    requests = get_key(user_info, ['requests'], [])
    return set([(request[0], request[1]) for request in requests])


def add_request(user_id, pin_code, age):
    user_id = int(user_id)
    pin_code = int(pin_code)
    age = int(age)

    user_info = get_or_create_user_info(user_id)
    if user_info is None:
        return 2

    requests = get_requests_userinfo(user_info)
    if len(requests) >= 4:
        return 1

    requests.add((pin_code, age))

    user_info['requests'] = [[i[0], i[1]] for i in requests]
    ret = update_user_info_set(user_id, user_info)
    if ret > 0:
        return 2

    return 0


def remove_request(user_id, pin_code, age):
    user_id = int(user_id)
    pin_code = int(pin_code)
    age = int(age)

    user_info = get_or_create_user_info(user_id)
    if user_info is None:
        return 2

    requests = get_requests_userinfo(user_info)
    if len(requests) == 0:
        return 1

    requests.remove((pin_code, age))

    user_info['requests'] = [[i[0], i[1]] for i in requests]
    ret = update_user_info_set(user_id, user_info)
    if ret > 0:
        return 2

    return 0


def remove_all_requests(user_id):
    user_id = int(user_id)

    try:
        db.userInfo.update_one({'userId': user_id}, update={'$unset': {'requests': 1}})
        return 0
    except Exception as e:
        logger.exception(e)
        return 1


def get_pincode_info(pincode):
    pincode = int(pincode)

    data = db.pinCodeInfo.find_one({'pincode': pincode})
    return data


def get_pincode_info_all():
    data = db.pinCodeInfo.find()
    return data


def update_pincode_info_set(pincode, pincode_info):
    pincode = int(pincode)

    try:
        curr_time = datetime.utcnow()
        last_modified_time = pincode_info.get('modifiedTime', datetime.fromtimestamp(0))

        pincode_info['modifiedTime'] = curr_time
        pincode_info['modifyTimeDiffSeconds'] = (curr_time - last_modified_time).total_seconds()

        db.pinCodeInfo.update_one({'pincode': pincode}, update={'$set': pincode_info})
        return 0
    except Exception as e:
        logger.exception(e)
        return 1


def create_pincode_info(pincode):
    pincode = int(pincode)

    try:
        data = {'pincode': pincode}
        db.pinCodeInfo.insert_one(document=data)
        return data
    except Exception as e:
        logger.exception(e)
        return None


def get_or_create_pincode_info(pincode):
    pincode = int(pincode)

    data = get_pincode_info(pincode)
    if data is None:
        data = create_pincode_info(pincode)
    return data


if __name__ == '__main__':
    admin_user_id = config['admin_user_id']

    res = update_user_info_set(admin_user_id, {
        'notificationState.c': {
            'timestamp': datetime.utcnow(),
            'type': 'p'
        }
    })
    logger.log(INFO, res)
