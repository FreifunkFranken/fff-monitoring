#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL

import urllib.request, urllib.error, json
import math

def update_hoods_v2(mysql):
	try:
		with urllib.request.urlopen("http://keyserver.freifunk-franken.de/v2/hoods.php") as url:
			hoodskx = json.loads(url.read().decode())
		
		kx_keys = []
		kx_data = []
		for kx in hoodskx:
			kx_keys.append(kx["id"])
			kx_data.append((kx["id"],kx["name"],kx["net"],kx.get("lat",None),kx.get("lon",None),))

		# Delete entries in DB where hood is missing in KeyXchange
		db_keys = mysql.fetchall("SELECT id FROM hoodsv2",(),"id")
		for n in db_keys:
			if n in kx_keys:
				continue
			mysql.execute("DELETE FROM hoodsv2 WHERE id = %s",(n,))

		# Create/update entries from KeyXchange to DB
		mysql.executemany("""
			INSERT INTO hoodsv2 (id, name, net, lat, lng)
			VALUES (%s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				name=VALUES(name),
				net=VALUES(net),
				lat=VALUES(lat),
				lng=VALUES(lng)
		""",kx_data)

	except urllib.error.HTTPError as e:
		return

def update_hoods_poly(mysql):
	try:
		#with urllib.request.urlopen("http://keyserver.freifunk-franken.de/v2/hoods.php") as url:
		with urllib.request.urlopen("https://lauch.org/keyxchange/hoods.php") as url:
			hoodskx = json.loads(url.read().decode())

		mysql.execute("DELETE FROM polygons",())
		mysql.execute("DELETE FROM polyhoods",())

		for kx in hoodskx:
			for polygon in kx.get("polygons",()):
				mysql.execute("""
					INSERT INTO polyhoods (hoodid)
					VALUES (%s)
				""",(kx["id"],))
				newid = mysql.cursor().lastrowid
				vertices = []
				for p in polygon:
					vertices.append((newid,p["lat"],p["lon"],))
				mysql.executemany("""
					INSERT INTO polygons (polyid, lat, lon)
					VALUES (%s, %s, %s)
				""",vertices)

	except urllib.error.HTTPError as e:
		return

def update_hoods_v1(mysql):
	try:
		with urllib.request.urlopen("http://keyserver.freifunk-franken.de/fff/hoods.php") as url:
			hoodskx = json.loads(url.read().decode())
		
		kx_keys = []
		kx_data = []
		for kx in hoodskx:
			if kx["id"]==0:
				continue # Skip Trainstation/NoCoordinates
			kx_keys.append(kx["id"])
			if kx.get("lat",None):
				cos_lat = math.cos(math.radians(kx["lat"]))
				sin_lat = math.sin(math.radians(kx["lat"]))
			else:
				cos_lat = None
				sin_lat = None
			kx["name"] = kx["name"][0].upper() + kx["name"][1:] + "V1"
			kx_data.append((kx["id"],kx["name"],kx["net"],kx.get("lat",None),kx.get("lon",None),cos_lat,sin_lat,))

		# Delete entries in DB where hood is missing in KeyXchange
		db_keys = mysql.fetchall("SELECT id FROM hoodsv1",(),"id")
		for n in db_keys:
			if n in kx_keys or n==0:
				continue
			mysql.execute("DELETE FROM hoodsv1 WHERE id = %s",(n,))

		# Create/update entries from KeyXchange to DB
		mysql.executemany("""
			INSERT INTO hoodsv1 (id, name, net, lat, lng, cos_lat, sin_lat)
			VALUES (%s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				name=VALUES(name),
				net=VALUES(net),
				lat=VALUES(lat),
				lng=VALUES(lng),
				cos_lat=VALUES(cos_lat),
				sin_lat=VALUES(sin_lat)
		""",kx_data)

	except urllib.error.HTTPError as e:
		return
