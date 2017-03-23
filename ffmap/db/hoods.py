#!/usr/bin/python

from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

# create db indexes
db.hoods.create_index([("position", "2dsphere")])

hoods = [
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
	"keyxchange_id": 7,
	"name": "wuerzburg",
	"net": "10.50.72.0/21",
	"position": {"type": "Point", "coordinates": [9.93489, 49.79688]}
},
{
	"keyxchange_id": 8,
	"name": "bamberg",
	"net": "10.50.124.0/22",
	"position": {"type": "Point", "coordinates": [10.95, 49.89]}
},
{
	"keyxchange_id": 9,
	"name": "bgl",
	"net": "10.50.80.0/21",
	"position": {"type": "Point", "coordinates": [12.8825, 47.7314]}
},
{
	"keyxchange_id": 10,
	"name": "HassbergeSued",
	"net": "10.50.60.0/22",
	"position": {"type": "Point", "coordinates": [10.568013390003, 50.04501]}
},
{
	"keyxchange_id": 11,
	"name": "nbgland",
	"net": "10.50.88.0/21",
	"position": {"type": "Point", "coordinates": [11.162796020507812, 49.39200496388418]}
},
{
        "keyxchange_id": 12,
        "name": "hof",
        "net": "10.50.104.0/21",
        "position": {"type": "Point", "coordinates": [11.9, 50.3]}
},
{
	"keyxchange_id": 13,
	"name": "aschaffenburg",
	"net": "10.50.96.0/22",
	"position": {"type": "Point", "coordinates": [9.886394, 49.986113]}
},
{
	"keyxchange_id": 14,
	"name": "marktredwitz",
	"net": "10.50.112.0/22",
	"position": {"type": "Point", "coordinates": [12.000519, 50.027736]}
},
{
	"keyxchange_id": 15,
	"name": "forchheim",
	"net": "10.50.116.0/22",
	"position": {"type": "Point", "coordinates": [11.1, 49.68]}
},
{
	"keyxchange_id": 16,
	"name": "muenchberg",
	"net": "10.50.120.0/22",
	"position": {"type": "Point", "coordinates": [11.79, 50.19]}
},
{
	"keyxchange_id": 17,
	"name": "adelsdorf",
	"net": "10.50.144.0/22",
	"position": {"type": "Point", "coordinates": [10.984488, 49.6035981]}
}]

for hood in hoods:
	db.hoods.insert_one(hood)
