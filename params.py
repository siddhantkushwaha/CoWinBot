import json
import os

root_dir = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(root_dir, "configs", "config.json"), "r") as fp:
    config = json.load(fp)

with open(os.path.join(root_dir, "configs", "token.json"), "r") as fp:
    tokens = json.load(fp)

raw_data_dir = os.path.join(root_dir, 'rawData')
