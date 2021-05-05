import json
import os

with open("token.json", "r") as fp:
    token = json.load(fp)["token"]

requests_dir = 'data/requests'
os.makedirs(requests_dir, exist_ok=True)

data_dir = 'data/cowin'
os.makedirs(data_dir, exist_ok=True)

raw_data_dir = 'rawData'
