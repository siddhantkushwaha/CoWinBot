from customLogging import get_logger
from db.database import Database
from params import config

db = Database()

logger = get_logger(log_name='db', log_level=5)


def get_user_info(user_id):
    data = None
    try:
        data = db.userInfo.find_one({'userId': user_id})
    except Exception as e:
        logger.exception(e)

    return data


def update_user_info_add_phone_number(user_id, phone_number):
    ret = 0
    try:
        user_info = db.userInfo.find_one({'userId': user_id})
        if user_info is None:
            user_info = {
                'userId': int(user_id),
                'phoneNumber': int(phone_number)
            }
            db.userInfo.insert_one(user_info)
        else:
            db.userInfo.update_one({'_id': user_info['_id']},
                                   update={'$set': {'phoneNumber': phone_number}})
    except Exception as e:
        ret = 1
        logger.exception(e)

    return ret


def set_meta(user_id, metaField, data):
    ret = 0
    try:
        user_info = db.userInfo.find_one({'userId': user_id})
        if user_info is None:
            ret = 2
        else:
            db.userInfo.update_one({'_id': user_info['_id']},
                                   update={'$set': {metaField: data}})
    except Exception as e:
        ret = 1
        logger.exception(e)

    return ret


if __name__ == '__main__':
    admin_user_id = config['admin_user_id']
    phone_number = '7351651000'

    obj_id = update_user_info_add_phone_number(admin_user_id, phone_number)
    print(obj_id)
