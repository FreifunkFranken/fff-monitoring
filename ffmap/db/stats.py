#!/usr/bin/python3

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

# create capped collection
db.create_collection("stats", capped=True, size=16*1024*1024, max=8640)
