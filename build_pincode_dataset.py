import os

import pandas as pd

from params import raw_data_dir
from util import save_pincode_set, save_pincode_dic

raw_data_pincode = pd.read_csv(os.path.join(raw_data_dir, 'all_india_pin_code.csv'))

pin_code_set = set(raw_data_pincode['pincode'])

save_pincode_set(pin_code_set)

pin_code_dic = {}
for i, row in raw_data_pincode.iterrows():
    pin_code_dic[row['pincode']] = {
        'divisionname': row['divisionname'],
        'regionname': row['regionname'],
        'circlename': row['circlename'],
        'Taluk': row['Taluk']
    }

save_pincode_dic(pin_code_dic)
