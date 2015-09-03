#!/usr/bin/python

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

for router in db.routers.find({"hood": {"$exists": True}, "neighbours": {"$exists": True}}):
	for neighbour in router["neighbours"]:
		if "_id" in neighbour and "position" in neighbour:
			neighbour_router = db.routers.find_one({"_id": neighbour["_id"]})
			if router["hood"] != neighbour_router["hood"]:
				print("Illegal inter-hood-mesh between %s (%s) and %s (%s)!" % (router["hostname"], router["hood"], neighbour_router["hostname"], neighbour_router["hood"]))
