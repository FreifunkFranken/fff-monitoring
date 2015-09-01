#!/usr/bin/python

import lxml.etree
import requests
import time
import subprocess
import gzip
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk
routers = db.routers

csv = open("routers.csv", "w")
csv.write("x,y,status\n")

#for router in routers.find({"bootstrap_ip": {"$exists": True}}):
for router in routers.find({}):
	csv.write("%f,%f,%s\n" % (router["position"]["lng"], router["position"]["lat"], router.get("status", "unknown")))

csv.close()
