import json
import os
import pickle

from params import raw_data_dir, notification_state_dir


def is_request_exists(user_request_path):
    return os.path.exists(user_request_path)


def load_request(user_request_path):
    user_request = {}
    if is_request_exists(user_request_path):
        with open(user_request_path, 'r') as fp:
            user_request = json.load(fp)

    return user_request


def save_request(user_request_path, user_request):
    with open(user_request_path, 'w') as fp:
        json.dump(user_request, fp)


def delete_request(user_request_path):
    if is_request_exists(user_request_path):
        os.remove(user_request_path)


def save_pincode_set(pincode_set):
    pt = os.path.join(raw_data_dir, 'pincode_set')
    with open(pt, 'wb') as fp:
        pickle.dump(pincode_set, fp)


def load_pincode_set():
    pt = os.path.join(raw_data_dir, 'pincode_set')
    with open(pt, 'rb') as fp:
        pincode_set = pickle.load(fp)
    return pincode_set


def save_pincode_dic(pincode_dic):
    pt = os.path.join(raw_data_dir, 'pincode_dic')
    with open(pt, 'wb') as fp:
        pickle.dump(pincode_dic, fp)


def load_pincode_dic():
    pt = os.path.join(raw_data_dir, 'pincode_dic')
    with open(pt, 'rb') as fp:
        pincode_dic = pickle.load(fp)
    return pincode_dic


def is_notification_state_exists(user_id):
    pt = os.path.join(notification_state_dir, f"{user_id}.pickle")
    return os.path.exists(pt)


def load_notification_state(user_id):
    pt = os.path.join(notification_state_dir, f"{user_id}.pickle")
    notification_state = {}
    if is_notification_state_exists(user_id):
        with open(pt, 'rb') as fp:
            notification_state = pickle.load(fp)

    return notification_state


def save_notification_state(user_id, notification_state):
    pt = os.path.join(notification_state_dir, f"{user_id}.pickle")
    with open(pt, 'wb') as fp:
        pickle.dump(notification_state, fp)
