import os

from db import dbHelper
from params import requests_dir
from util import load_request


def migrate_requests_disk_to_db():
    requests = os.listdir(requests_dir)
    for pt in requests:
        if pt.endswith('.json'):
            user_id = pt.replace('.json', '')
            pt = os.path.join(requests_dir, pt)
            user_request = load_request(pt)
            user_request_set = [i.split('_') for i in set(user_request.get('request', []))]
            for item in user_request_set:
                ret = dbHelper.add_request(user_id, item[0], item[1])
                if ret > 0:
                    print(f'Failed to added request: [{user_id}], [{item}], [{ret}].')


if __name__ == '__main__':
    migrate_requests_disk_to_db()
