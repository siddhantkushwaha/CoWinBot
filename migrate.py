import json
import os

from db import dbHelper
from params import requests_dir


def is_request_exists(user_request_path):
    return os.path.exists(user_request_path)


def load_request(user_request_path):
    user_request = {}
    if is_request_exists(user_request_path):
        with open(user_request_path, 'r') as fp:
            user_request = json.load(fp)

    return user_request


def delete_request(user_request_path):
    if is_request_exists(user_request_path):
        os.remove(user_request_path)


def migrate_requests_disk_to_db():
    requests = os.listdir(requests_dir)
    for pt in requests:
        if pt.endswith('.json'):
            user_id = pt.replace('.json', '')
            pt = os.path.join(requests_dir, pt)
            user_request = load_request(pt)
            user_request_set = [i.split('_') for i in set(user_request.get('request', []))]

            failed = False
            for item in user_request_set:
                ret = dbHelper.add_request(user_id, item[0], item[1])
                if ret > 0:
                    print(f'Failed to add request: [{user_id}], [{item}], [{ret}].')
                    failed = True
                    break

            if not failed:
                delete_request(pt)


if __name__ == '__main__':
    migrate_requests_disk_to_db()
