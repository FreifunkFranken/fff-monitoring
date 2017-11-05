#!/usr/bin/python

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL
import math

mysql = FreifunkMySQL()

hoods = [
{
	"keyxchange_id": 1,
	"name": "Default",
	"net": "10.50.16.0/20"
},
{
	"keyxchange_id": 2,
	"name": "Fuerth",
	"net": "10.50.32.0/21",
	"position": {"lng": 10.966, "lat": 49.4814}
},
{
	"keyxchange_id": 3,
	"name": "Nuernberg",
	"net": "10.50.40.0/21",
	"position": {"lng": 11.05, "lat": 49.444}
},
{
	"keyxchange_id": 4,
	"name": "Ansbach",
	"net": "10.50.48.0/21",
	"position": {"lng": 10.571667, "lat": 49.300833}
},
{
	"keyxchange_id": 5,
	"name": "Hassberge",
	"net": "10.50.56.0/21",
	"position": {"lng": 10.568013390003, "lat": 50.093555895082}
},
{
	"keyxchange_id": 6,
	"name": "Erlangen",
	"net": "10.50.64.0/21",
	"position": {"lng": 11.0019221, "lat": 49.6005981}
},
{
	"keyxchange_id": 7,
	"name": "Wuerzburg",
	"net": "10.50.72.0/21",
	"position": {"lng": 9.93489, "lat": 49.79688}
},
{
	"keyxchange_id": 8,
	"name": "Bamberg",
	"net": "10.50.124.0/22",
	"position": {"lng": 10.95, "lat": 49.89}
},
{
	"keyxchange_id": 9,
	"name": "BGL",
	"net": "10.50.80.0/21",
	"position": {"lng": 12.8825, "lat": 47.7314}
},
{
	"keyxchange_id": 10,
	"name": "HassbergeSued",
	"net": "10.50.60.0/22",
	"position": {"lng": 10.568013390003, "lat": 50.04501}
},
{
	"keyxchange_id": 11,
	"name": "NbgLand",
	"net": "10.50.88.0/21",
	"position": {"lng": 11.162796020507812, "lat": 49.39200496388418}
},
{
	"keyxchange_id": 12,
	"name": "Hof",
	"net": "10.50.104.0/21",
	"position": {"lng": 11.917545, "lat": 50.312209}
},
{
	"keyxchange_id": 13,
	"name": "Aschaffenburg",
	"net": "10.50.96.0/22",
	"position": {"lng": 9.146826, "lat": 49.975661}
},
{
	"keyxchange_id": 14,
	"name": "Marktredwitz",
	"net": "10.50.112.0/22",
	"position": {"lng": 12.084797, "lat": 50.002915}
},
{
	"keyxchange_id": 15,
	"name": "Forchheim",
	"net": "10.50.116.0/22",
	"position": {"lng": 11.059474, "lat": 49.718820}
},
{
	"keyxchange_id": 16,
	"name": "Muenchberg",
	"net": "10.50.120.0/22",
	"position": {"lng": 11.79, "lat": 50.19}
},
{
	"keyxchange_id": 17,
	"name": "Adelsdorf",
	"net": "10.50.144.0/22",
	"position": {"lng": 10.894235, "lat": 49.709945}
},
{
	"keyxchange_id": 18,
	"name": "Schweinfurt",
	"net": "10.50.160.0/22",
	"position": {"lng": 10.21267, "lat": 50.04683}
},
{
	"keyxchange_id": 19,
	"name": "ErlangenWest",
	"net": "10.50.152.0/22",
	"position": {"lng": 10.984488, "lat": 49.6035981}
},
{
	"keyxchange_id": 20,
	"name": "Ebermannstadt",
	"net": "10.50.148.0/22",
	"position": {"lng": 11.18538, "lat": 49.78173}
},
{
	"keyxchange_id": 21,
	"name": "Lauf",
	"net": "10.50.156.0/22",
	"position": {"lng": 11.278789, "lat": 49.509972}
},
{
	"keyxchange_id": 22,
	"name": "Bayreuth",
	"net": "10.50.168.0/22",
	"position": {"lng": 11.580566, "lat": 49.94814}
},
{
	"keyxchange_id": 23,
	"name": "Fichtelberg",
	"net": "10.50.172.0/22",
	"position": {"lng": 11.852292, "lat": 49.998920}
},
{
	"keyxchange_id": 24,
	"name": "Rehau",
	"net": "10.50.176.0/22",
	"position": {"lng": 12.035305, "lat": 50.247594}
},
	{
	"keyxchange_id": 25,
	"name": "Coburg",
	"net": "10.50.180.0/22",
	"position": {"lng": 10.964414, "lat": 50.259675}
},
{
	"keyxchange_id": 26,
	"name": "Ebern",
	"net": "10.50.184.0/22",
	"position": {"lng": 10.798395, "lat": 50.095572}
},
{
	"keyxchange_id": 27,
	"name": "Arnstein",
	"net": "10.50.188.0/22",
	"position": {"lng": 9.970957, "lat": 49.978117}
},
{
	"keyxchange_id": 28,
	"name": "Erlenbach",
	"net": "10.50.192.0/22",
	"position": {"lng": 9.157491, "lat": 49.803930}
}]

for h in hoods:
	coord = h.get("position",{})
	if coord.get("lat"):
		cos_lat = math.cos(math.radians(coord.get("lat")))
		sin_lat = math.sin(math.radians(coord.get("lat")))
	else:
		cos_lat = None
		sin_lat = None
	
	mysql.execute("""
		INSERT INTO hoods (id, name, net, lat, lng, cos_lat, sin_lat)
		VALUES (%s, %s, %s, %s, %s, %s, %s)
	""",(h["keyxchange_id"],h["name"],h["net"],coord.get("lat"),coord.get("lng"),cos_lat,sin_lat,))

mysql.commit()
mysql.close()
