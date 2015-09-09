#!/usr/bin/python

import subprocess
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

# this tool will try to show you the hostname of the Freifunk AP you are currently connected to

mac = subprocess.check_output(["iwgetid", "-ar"]).strip().lower().decode()

router = db.routers.find_one({"netifs.mac": mac})

print(router["hostname"])
