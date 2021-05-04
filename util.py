import json
import os


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
