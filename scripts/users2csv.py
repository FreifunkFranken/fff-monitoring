#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from pymongo import MongoClient
from bson.json_util import dumps as bson2json
from bson.objectid import ObjectId
import base64
import datetime

targetfile = "/data/fff/users.txt"

client = MongoClient(tz_aware=True, connect=False)
db = client.freifunk

users = db.users.find({}, {"nickname": 1, "password":1, "email": 1, "token": 1, "created": 1, "admin": 1})

with open(targetfile, "w") as csv:
	for u in users:
		csv.write("%s;%s;%s;%s;%s;%s\n" % (u.get("nickname"),u.get("token"),u.get("email",""),u.get("created"),u.get("admin",0),u.get("password")))
