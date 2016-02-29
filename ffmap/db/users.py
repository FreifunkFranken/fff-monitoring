#!/usr/bin/python3

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

# create db indexes
db.users.create_index("email")
db.users.create_index("nickname")
