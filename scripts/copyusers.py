#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL

import pymongo
from bson.json_util import dumps as bson2json
from bson.objectid import ObjectId
import base64
import datetime

client = MongoClient(tz_aware=True, connect=False)
db = client.freifunk

users = db.users.find({}, {"nickname": 1, "password":1, "email": 1, "token": 1, "created": 1, "admin": 1})

mysql = FreifunkMySQL()
cur = mysql.cursor()
for u in users:
	#print(u)
	cur.execute("""
		INSERT INTO users (nickname, password, token, email, created, admin)
		VALUES (%s, %s, %s, %s, %s, %s)
	""",(u.get("nickname"),u.get("password"),u.get("token"),u.get("email",""),u.get("created"),u.get("admin",0),))
mysql.commit()
mysql.close()
