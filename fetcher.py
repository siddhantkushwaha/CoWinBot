import json
from datetime import datetime

from customLogging import get_logger, DATA, DEBUG, INFO, WARNING
from db import dbHelper
from params import root_dir
from pincode_data import is_pincode_valid
from util import get_key, ist_time

logger = get_logger('fetcher', path=root_dir, log_level=5)


def check_slots_available(pincode_info, pincode, age):
    logger.log(INFO, f'Check slots for pincode [{pincode}].')

    pincode_data = get_key(pincode_info, ['meta'])
    latest_timestamp = get_key(pincode_info, ['modifiedTime'], datetime.fromtimestamp(0))

    curr_time = datetime.utcnow()
    time_diff = curr_time - latest_timestamp
    is_data_within_one_day = time_diff.total_seconds() < 24 * 3600

    logger.log(DEBUG, f'For pincode [{pincode}], data exists: '
                      f'[{pincode_data is not None}], is data recent: [{is_data_within_one_day}].')

    slots_data = {}

    # if date available for this pincode is too old, discard it
    if pincode_data is not None and is_data_within_one_day:
        pincode_data = json.loads(pincode_data)
        for center in pincode_data['centers']:
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

                if min_age <= age and capacity > 0:
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


def check_slot_get_response(pincode_info, pincode, age):
    logger.log(INFO, f'Build response after checking slots for pincode [{pincode}].')

    response = ['']

    pincode = int(pincode)
    age = int(age)

    timestamp, slots = check_slots_available(pincode_info, pincode, age)
    timestamp_str = ist_time(timestamp).strftime('%d-%m-%Y %I:%M %p')

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

            for session in values['sessions']:
                session_capacity = session['capacity']

                session_capacity_str = str(session_capacity)
                if session_capacity <= 4:
                    session_capacity_str += " (Someone probably canceled their appointment.)"

                session_string = f"\n\nDate: {session['date']}" \
                                 f"\nVaccine name: {session['vaccine']}" \
                                 f"\nMinimum age: {session['min_age']}" \
                                 f"\nCapacity: {session_capacity_str}" \
                                 f"\nSlots: {', '.join(session['slots'])}"

                center_string += session_string

            center_string = center_string.strip()
            response.append(center_string)

    logger.log(INFO, f'Response type [{response_type}] for pincode [{pincode}], age [{age}].')
    logger.log(DATA, response)

    return response_type, response


def get_all_pincodes(all_user_info):
    logger.log(INFO, 'Fetching pincodes from existing user requests.')

    pincodes = set()
    invalid_pincodes = set()

    for user_info in all_user_info:
        user_request = dbHelper.get_requests_userinfo(user_info)
        for pincode, age in user_request:
            if is_pincode_valid(pincode):
                pincodes.add(pincode)
            else:
                invalid_pincodes.add(pincode)

    logger.log(DATA, f'Valid pincodes => {pincodes}')
    if len(invalid_pincodes) > 0:
        logger.log(WARNING, f'Invalid pincodes found => {invalid_pincodes}')

    return pincodes


def build_user_requests_by_pincode(all_user_info):
    res = {}

    for user_info in all_user_info:
        user_id = user_info['userId']
        user_request = dbHelper.get_requests_userinfo(user_info)

        for pincode, age in user_request:
            by_pincode = res.get(pincode, set())
            by_pincode.add((user_id, age))
            res[pincode] = by_pincode

    return res
