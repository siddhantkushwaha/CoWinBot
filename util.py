import os
import pickle

from params import raw_data_dir


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


def get_key(obj, keys, if_none_val=None):
    for key in keys:
        if obj is None:
            break
        obj = obj.get(key, None)

    if obj is None and if_none_val is not None:
        obj = if_none_val

    return obj
