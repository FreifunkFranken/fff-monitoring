#!/usr/bin/python3

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

for router in db.routers.find({"hood": {"$exists": True}, "neighbours": {"$exists": True}, "status": "online"}, {"stats": 0}):
	for neighbour in router["neighbours"]:
		if "_id" in neighbour and "position" in neighbour:
			neighbour_router = db.routers.find_one({"_id": neighbour["_id"]}, {"stats": 0})
			if router["hood"] != neighbour_router["hood"] and neighbour_router["status"] == "online":
				print("Illegal inter-hood-mesh between %s (%s) and %s (%s)!" % (router["hostname"], router["hood"], neighbour_router["hostname"], neighbour_router["hood"]))
