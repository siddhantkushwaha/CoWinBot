import json
import os

root_dir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(root_dir, "configs", "config.json"), "r") as fp:
    config = json.load(fp)

with open(os.path.join(root_dir, "configs", "token.json"), "r") as fp:
    tokens = json.load(fp)

requests_dir = os.path.join(root_dir, 'data', 'requests')
os.makedirs(requests_dir, exist_ok=True)

data_dir = os.path.join(root_dir, 'data', 'cowin')
os.makedirs(data_dir, exist_ok=True)

notification_state_dir = os.path.join(root_dir, 'data', 'notificationState')
os.makedirs(notification_state_dir, exist_ok=True)

raw_data_dir = os.path.join(root_dir, 'rawData')