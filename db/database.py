from pymongo import MongoClient

from params import config


class Database:

    def __init__(self):
        self.client = MongoClient(config['db_url'])
        self.db = self.client.cowin

    @property
    def userInfo(self):
        return self.db['userInfo']
