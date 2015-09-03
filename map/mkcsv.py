#!/usr/bin/python

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

with open("csv/routers.csv", "w") as csv:
	csv.write("lng,lat,status\n")
	for router in db.routers.find({"position.coordinates": {"$exists": True}}):
		csv.write("%f,%f,%s\n" % (
			router["position"]["coordinates"][0],
			router["position"]["coordinates"][1],
			router.get("status", "unknown")
		))

with open("csv/links.csv", "w") as csv:
	csv.write("WKT,quality\n")
	for router in db.routers.find({"position.coordinates": {"$exists": True}, "neighbours": {"$exists": True}}):
		for neighbour in router["neighbours"]:
			if "position" in neighbour:
				csv.write("\"LINESTRING (%f %f,%f %f)\",%i\n" % (
					router["position"]["coordinates"][0],
					router["position"]["coordinates"][1],
					neighbour["position"]["coordinates"][0],
					neighbour["position"]["coordinates"][1],
					neighbour["quality"]
				))
