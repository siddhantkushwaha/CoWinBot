import json
import os
import time
from datetime import datetime

import requests

from customLogging import get_logger, DATA, DEBUG, INFO, WARNING
from params import data_dir, requests_dir
from util import load_request, delete_request, load_pincode_set

logger = get_logger('fetcher', log_level=5)


def get_path_for_pincode(pincode):
    return os.path.join(data_dir, str(pincode))


def fetch_latest_timestamp_pincode(pincode):
    logger.log(INFO, f'Getting latest timestamp for pincode [{pincode}].')

    timestamp = 0
    pincode_dir = get_path_for_pincode(pincode)
    if not os.path.exists(pincode_dir):
        logger.log(WARNING, f'Not data found for pincode [{pincode}].')
    else:

        li = os.listdir(pincode_dir)
        li = filter(lambda p: p.endswith('.json'), li)
        li = map(lambda p: int(p.replace('.json', '').strip()), li)

        timestamp = max(li, default=0)

    logger.log(INFO, f'Latest timestamp for [{pincode}] is [{timestamp}].')
    return timestamp


def check_slots_available(pincode, age):
    logger.log(INFO, f'Check slots for pincode [{pincode}].')

    latest_timestamp = fetch_latest_timestamp_pincode(pincode)

    curr_time = datetime.now()
    time_diff = curr_time - datetime.fromtimestamp(latest_timestamp)

    data_by_pincode_path = os.path.join(get_path_for_pincode(pincode), f'{latest_timestamp}.json')

    slots_data = {}

    is_data_file_exists = os.path.exists(data_by_pincode_path)
    is_data_within_one_day = time_diff.total_seconds() < 24 * 3600

    logger.log(DEBUG, f'For pincode [{pincode}], data file exists: '
                      f'[{is_data_file_exists}], is data recent: [{is_data_within_one_day}].')

    # if date available for this pincode is too old, disregard it
    if is_data_file_exists and is_data_within_one_day:
        with open(data_by_pincode_path, 'r') as fp:
            data_by_pincode = json.load(fp)

        for center in data_by_pincode['centers']:
            name = center['name']
            address = center['address']
            state = center['state_name']
            district = center['district_name']
            block = center['block_name']
            pin_code_in_data = center['pincode']
            lat = center['lat']
            long = center['long']
            from_time = center['from']
            to_time = center['to']
            fee_type = center['fee_type']

            for session in center['sessions']:
                date = session['date']
                min_age = session['min_age_limit']
                capacity = session['available_capacity']
                vaccine = session['vaccine']
                slots = session['slots']

                if min_age <= age:
                    center_data = slots_data.get(name, {})
                    slots_data[name] = {
                        'name': name,
                        'address': address,
                        'block': block,
                        'district': district,
                        'state': state,
                        'pincode': pin_code_in_data,
                        'latlng': (lat, long),
                        'from_time': from_time,
                        'to_time': to_time,
                        'fee_type': fee_type
                    }

                    sessions = center_data.get('sessions', [])
                    sessions.append({
                        'date': date,
                        'min_age': min_age,
                        'capacity': capacity,
                        'vaccine': vaccine,
                        'slots': slots
                    })

                    slots_data[name]['sessions'] = sessions

        logger.log(INFO, f'For pincode [{pincode}], age [{age}], slots found at [{latest_timestamp}].')
        logger.log(DATA, slots_data)
        return latest_timestamp, slots_data
    else:
        logger.log(INFO, f'No slots found for pincode [{pincode}], age [{age}].')
        return latest_timestamp, None


def check_slot_get_response(pincode, age):
    logger.log(INFO, f'Build response after checking slots for pincode [{pincode}].')

    response = ['']

    pincode = int(pincode)
    age = int(age)

    timestamp, slots = check_slots_available(pincode, age)
    timestamp = datetime.fromtimestamp(timestamp)
    timestamp_str = timestamp.strftime('%d-%m-%Y %I:%M %p')

    if slots is None:
        response_type = 'none'
        response[0] = f'Information for this pincode not available. ' \
                      f'Your request has been registered, please wait for some time while we fetch ' \
                      f'information requested by you.'
    elif len(slots) == 0:
        response_type = 'negative'
        response[0] = f'No slots in this pincode available as of {timestamp_str}. Your request has been registered, ' \
                      'Notification will be sent when slot is available.'
    else:
        response_type = 'positive'
        response = []
        for center_name, values in slots.items():
            center_string = f"\n\n{values['name']}, {values['address']}, {values['block']}, " \
                            f"{values['district']}, {values['pincode']}, {values['state']}" \
                            f"\nTime: {values['from_time']} to {values['to_time']}" \
                            f"\nFee: {values['fee_type']}"

            sessions_with_availability = 0
            for session in values['sessions']:
                if session['capacity'] > 0:
                    sessions_with_availability += 1

                    session_string = f"\n\nDate: {session['date']}" \
                                     f"\nVaccine name: {session['vaccine']}" \
                                     f"\nMinimum age: {session['min_age']}" \
                                     f"\nCapacity: {session['capacity']}" \
                                     f"\nSlots: {', '.join(session['slots'])}"

                    center_string += session_string

            if sessions_with_availability == 0:
                center_string = "All appointments are booked for this center." + center_string

            center_string = center_string.strip()
            response.append(center_string)

    logger.log(INFO, f'Response type [{response_type}] for pincode [{pincode}], age [{age}].')
    logger.log(DATA, response)

    return response_type, response


def parse_pincode_age_requests():
    logger.log(INFO, f'Parsing all requests collected by bot(s).')

    all_req = {}

    for req_file in os.listdir(requests_dir):
        if not req_file.endswith('.json'):
            continue

        req_file_path = os.path.join(requests_dir, req_file)

        user_request = load_request(req_file_path)

        user_id = int(req_file.replace('.json', ''))
        user_requests = []
        for item in user_request['request']:
            item_split = item.split('_')
            user_requests.append((int(item_split[0]), int(item_split[1])))

        if len(user_requests) > 0:
            all_req[user_id] = user_requests
        else:
            delete_request(req_file_path)

    logger.log(INFO, f'All requests parsed.')
    logger.log(DATA, all_req)

    return all_req


def get_all_pincodes(all_req):
    logger.log(INFO, 'Fetching pincodes from existing user requests.')

    valid_pincode_set = load_pincode_set()

    pincodes = set()
    invalid_pincodes = set()

    for user_id, req in all_req.items():
        for i in req:
            pincode = int(i[0])
            if pincode in valid_pincode_set:
                pincodes.add(pincode)
            else:
                invalid_pincodes.add(pincode)

    logger.log(DATA, f'Valid pincodes => {pincodes}')
    if len(invalid_pincodes) > 0:
        logger.log(WARNING, f'Invalid pincodes found => {invalid_pincodes}')

    return pincodes


def fetch(all_req, min_time_diff_seconds):
    priority_pincodes = {263139}

    pincodes = get_all_pincodes(all_req)
    for pincode in pincodes:
        logger.log(INFO, f'Fetching for pincode [{pincode}].')

        curr_timestamp = datetime.now()
        date_today = curr_timestamp.strftime('%d-%m-%Y')

        last_timestamp = fetch_latest_timestamp_pincode(pincode)
        last_timestamp = datetime.fromtimestamp(last_timestamp)

        time_diff_seconds = (curr_timestamp - last_timestamp).total_seconds()
        if pincode not in priority_pincodes and time_diff_seconds < min_time_diff_seconds:
            logger.log(INFO, f'Skipping pincode [{pincode}] because it was '
                             f'already fetched within last [{time_diff_seconds}] seconds.')
            continue

        url = f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/' \
              f'public/calendarByPin?pincode={pincode}&date={date_today}'

        logger.log(DEBUG, f'API url for pincode [{pincode}] is [{url}].')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
        }
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            exception = Exception(f'Failed to fetch data for pincode [{pincode}], '
                                  f'response code [{response.status_code}].')
            logger.exception(exception)
            raise exception

        data = json.loads(response.content)

        pt = get_path_for_pincode(pincode)
        os.makedirs(pt, exist_ok=True)

        data_path = os.path.join(pt, f"{curr_timestamp.strftime('%s')}.json")
        with open(data_path, 'w') as fp:
            json.dump(data, fp)

        logger.log(INFO, f'Date fetch success for [{pincode}] at location [{data_path}].')

        # Go easy on the api
        time.sleep(10)
