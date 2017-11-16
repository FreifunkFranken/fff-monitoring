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

import csv

targetfile = "/data/fff/users.txt"

mysql = FreifunkMySQL()
data = []
with open(targetfile, newline='') as csvfile:
	spamreader = csv.reader(csvfile, delimiter=';')
	for row in spamreader:
		if row[5]=="None":
			row[5]=None
		if row[1]=="None":
			row[1]=None
		if row[1]=="None":
			row[1]=None
		if row[2]=="None":
			row[2]=None
		if row[3]=="None":
			row[3]=None
		if row[4]=="True":
			row[4]=1
		else:
			row[4]=0
		row[3] = datetime.datetime.strptime(''.join(row[3].rsplit(':', 1)),"%Y-%m-%d %H:%M:%S.%f%z").strftime('%Y-%m-%d %H:%M:%S')

		data.append((row[0],row[5],row[1],row[2],row[3],row[4],))

mysql.executemany("""
	INSERT INTO users (nickname, password, token, email, created, admin)
	VALUES (%s, %s, %s, %s, %s, %s)
""",data)
mysql.commit()
mysql.close()
