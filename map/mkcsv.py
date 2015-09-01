#!/usr/bin/python

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk
routers = db.routers

with open("csv/routers.csv", "w") as csv:
	csv.write("lng,lat,status\n")
	for router in routers.find({"position.lat": {"$exists": True}, "position.lng": {"$exists": True}}):
		csv.write("%f,%f,%s\n" % (router["position"]["lng"], router["position"]["lat"], router.get("status", "unknown")))

with open("csv/links.csv", "w") as csv:
	csv.write("WKT,quality\n")
	for router in routers.find({"position.lat": {"$exists": True}, "position.lng": {"$exists": True}, "neighbours": {"$exists": True}}):
		for neighbour in router["neighbours"]:
			if not "_id" in neighbour:
				continue
			neighbour_router = routers.find_one({"_id": neighbour["_id"], "position.lat": {"$exists": True}, "position.lng": {"$exists": True}})
			if neighbour_router:
				csv.write("\"LINESTRING (%f %f,%f %f)\",%i\n" % (
					router["position"]["lng"],
					router["position"]["lat"],
					neighbour_router["position"]["lng"],
					neighbour_router["position"]["lat"],
					neighbour["quality"]
				))
