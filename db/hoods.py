#!/usr/bin/python

from math import sin, cos, sqrt, atan2, radians
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

CONFIG = {"default_hood_id": 1}

"""
db.hoods.insert_many([
{
	"keyxchange_id": 1,
	"name": "transition",
	"net": "10.50.16.0/20"
},
{
	"keyxchange_id": 2,
	"name": "fuerth",
	"net": "10.50.32.0/21",
	"position": {"lat": 49.478330, "lng": 10.990270}
},
{
	"keyxchange_id": 3,
	"name": "nuernberg",
	"net": "10.50.40.0/21",
	"position": {"lat": 49.448856, "lng": 11.082108}
},
{
	"keyxchange_id": 4,
	"name": "ansbach",
	"net": "10.50.48.0/21",
	"position": {"lat": 49.300833, "lng": 10.571667}
},
{
	"keyxchange_id": 5,
	"name": "haßberge",
	"net": "10.50.56.0/21",
	"position": {"lat": 50.093555, "lng": 10.568013}
},
{
	"keyxchange_id": 6,
	"name": "erlangen",
	"net": "10.50.64.0/21",
	"position": {"lat": 49.600598, "lng": 11.001922}
},
{
	"keyxchange_id": 6,
	"name": "wuerzburg",
	"net": "10.50.72.0/21",
	"position": {"lat": 49.796880, "lng":  9.934890}
}])
"""

def km_distance(pos1, pos2):
	lng1 = radians(pos1["lng"])
	lat1 = radians(pos1["lat"])
	lng2 = radians(pos2["coordinates"][0])
	lat2 = radians(pos2["coordinates"][1])

	dlng = lng2 - lng1
	dlat = lat2 - lat1

	a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
	c = 2 * atan2(sqrt(a), sqrt(1 - a))

	# approximate radius of earth in km
	R = 6373.0

	distance = R * c

	return distance

def hood_by_pos(pos):
	current_hood_dist = 99999999
	current_hood = db.hoods.find({"keyxchange_id": CONFIG["default_hood_id"]})

	for hood in db.hoods.find({"position": {"$exists": True}}):
		distance = km_distance(hood["position"], pos)
		if distance <= current_hood_dist:
			current_hood_dist = distance
			current_hood = hood
	
	return current_hood
