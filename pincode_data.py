import os

import pandas as pd

from params import raw_data_dir
from util import load_pincode_set, load_pincode_dic, save_pincode_set, save_pincode_dic

pin_code_set = load_pincode_set()
pin_code_dic = load_pincode_dic()


def build():
    raw_data_pincode = pd.read_csv(os.path.join(raw_data_dir, 'all_india_pin_code.csv'))

    pin_code_set = set(raw_data_pincode['pincode'])
    save_pincode_set(pin_code_set)

    columns = list(raw_data_pincode.columns)
    pin_code_dic = {}
    for i, row in raw_data_pincode.iterrows():
        pin_code_dic[row['pincode']] = {column: row[column] for column in columns}

    save_pincode_dic(pin_code_dic)


def is_pincode_valid(pincode):
    return pincode in pin_code_set


def beautify(string):
    return ' '.join([i.capitalize() for i in str(string).lower().split()])


def get_address_by_pincode(pincode):
    pincode_info = pin_code_dic[pincode]

    state = beautify(pincode_info['statename'])
    district = beautify(pincode_info['Districtname'])
    taluk = beautify(pincode_info['Taluk'])

    response = f"{taluk}, {district}, {state}"
    return response
