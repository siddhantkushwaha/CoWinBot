import json
import time

import requests

from db import dbHelper
from params import config
from pincode_data import get_address_by_pincode
from util import get_key

token = config['mapbox_key']


def update_pincode_maps_info(pincode):
    params = {
        'types': 'place',
        'country': 'IN',
        'worldview': 'in'
    }

    query = get_address_by_pincode(pincode)
    print(query)

    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{query}.json?access_token={token}"

    response = requests.get(url, params)

    print(response.status_code)
    if response.status_code == 200:
        data = json.loads(response.content.decode())
        features = get_key(data, ['features'])
        if len(features) > 0:
            feature_max_relevance = max(features, key=lambda x: x['relevance'])
            ret = dbHelper.update_pincode_info_set(pincode, {'mapboxFeatures': json.dumps(feature_max_relevance)})
            if ret > 0:
                print('Failed to update.')


def run():
    pincodes = dbHelper.get_pincode_info_all(filters={'mapboxFeatures': {'$exists': 0}}, sort=[('_id', 1)])
    for pincode in pincodes:
        pincode = int(pincode['pincode'])
        update_pincode_maps_info(pincode)
        time.sleep(1)


if __name__ == '__main__':
    run()
