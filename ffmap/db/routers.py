#!/usr/bin/python3

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

# create db indexes
db.routers.create_index("hostname")
db.routers.create_index("status")
db.routers.create_index("created")
db.routers.create_index("last_contact")
db.routers.create_index("netifs.mac")
db.routers.create_index([("position", "2dsphere")])
