#!/usr/bin/python

from math import sin, cos, sqrt, atan2, radians
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

CONFIG = {"default_hood_id": 1}

"""
# create db indexes
db.hoods.create_index([("position", "2dsphere")])
db.hoods.insert_many([
{
	"keyxchange_id": 1,
	"name": "default",
	"net": "10.50.16.0/20"
},
{
	"keyxchange_id": 2,
	"name": "fuerth",
	"net": "10.50.32.0/21",
	"position": {"type": "Point", "coordinates": [10.966, 49.4814]}
},
{
	"keyxchange_id": 3,
	"name": "nuernberg",
	"net": "10.50.40.0/21",
	"position": {"type": "Point", "coordinates": [11.05, 49.444]}
},
{
	"keyxchange_id": 4,
	"name": "ansbach",
	"net": "10.50.48.0/21",
	"position": {"type": "Point", "coordinates": [10.571667, 49.300833]}
},
{
	"keyxchange_id": 5,
	"name": "haßberge",
	"net": "10.50.56.0/21",
	"position": {"type": "Point", "coordinates": [10.568013390003, 50.093555895082]}
},
{
	"keyxchange_id": 6,
	"name": "erlangen",
	"net": "10.50.64.0/21",
	"position": {"type": "Point", "coordinates": [11.0019221, 49.6005981]}
},
{
	"keyxchange_id": 6,
	"name": "wuerzburg",
	"net": "10.50.72.0/21",
	"position": {"type": "Point", "coordinates": [9.93489, 49.79688]}
},
{
	"keyxchange_id": 7,
	"name": "bgl",
	"net": "10.50.80.0/21",
	"position": {"type": "Point", "coordinates": [12.8825, 47.7314]}
},
{
	"keyxchange_id": 8,
	"name": "HassbergeSued",
	"net": "10.50.60.0/22",
	"position": {"type": "Point", "coordinates": [10.568013390003, 50.08]}
}])
"""

def km_distance(lng1, lat1, lng2, lat2):
	lng1 = radians(lng1)
	lat1 = radians(lat1)
	lng2 = radians(lng2)
	lat2 = radians(lat2)

	dlng = lng2 - lng1
	dlat = lat2 - lat1

	a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlng / 2)**2
	c = 2 * atan2(sqrt(a), sqrt(1 - a))

	# approximate radius of earth in km
	R = 6373.0

	distance = R * c

	return distance

def hood_by_pos(lng, lat):
	current_hood_dist = 99999999
	current_hood = db.hoods.find({"keyxchange_id": CONFIG["default_hood_id"]})

	for hood in db.hoods.find({"position": {"$exists": True}}):
		distance = km_distance(hood["position"]["lng"], hood["position"]["lat"], lng, lat)
		if distance <= current_hood_dist:
			current_hood_dist = distance
			current_hood = hood
	
	return current_hood
