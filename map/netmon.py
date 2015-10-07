#!/usr/bin/python

import lxml.etree
import requests
import datetime
from pymongo import MongoClient

client = MongoClient()
db = client.freifunk

def fetch_router_info(mac):
	mac = mac.replace(":", "").lower()
	tree = lxml.etree.fromstring(requests.get("https://netmon.freifunk-franken.de/api/rest/router/%s" % mac, params={"limit": 5000}).content)

	for r in tree.xpath("/netmon_response/router"):
		user_netmon_id = int(r.xpath("user_id/text()")[0])
		user = db.users.find_one({"netmon_id": user_netmon_id})
		if user:
			user_id = user["_id"]
		else:
			user_id = db.users.insert({
				"netmon_id": user_netmon_id,
				"nickname": r.xpath("user/nickname/text()")[0]
			})
			user = db.users.find_one({"_id": user_id})

		router = {
			"netmon_id": int(r.xpath("router_id/text()")[0]),
			"user": {"nickname": user["nickname"], "_id": user["_id"]}
		}

		try:
			lng = float(r.xpath("longitude/text()")[0])
			lat = float(r.xpath("latitude/text()")[0])
			assert lng != 0
			assert lat != 0

			router["position"] = {
				"type": "Point",
				"coordinates": [lng, lat]
			}

			# try to get comment
			position_comment = r.xpath("location/text()")[0]
			if position_comment != "undefined":
				router["position"]["comment"] = position_comment
		except (IndexError, AssertionError):
			pass

		try:
			router["description"] = r.xpath("description/text()")[0]
		except IndexError:
			pass

		router["last_contact"] = datetime.datetime.utcnow()
		router["created"] = datetime.datetime.utcnow()

		return router
