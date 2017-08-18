#!/usr/bin/python3

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

# create capped collection
db.create_collection("stats", capped=True, size=10*1024*1024, max=4320)
db.create_collection("hoodstats", capped=True, size=10*1024*1024, max=4320)
