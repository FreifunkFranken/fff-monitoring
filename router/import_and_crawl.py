#!/usr/bin/python

import lxml.etree
import requests
import time
import subprocess
import gzip
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk
routers = db.routers

#routers.find_one()

# r.xml is the router kml file from the netmon map
"""
tree = lxml.etree.parse("/tmp/r.xml")

for p in tree.xpath("/kml/Folder/Placemark"):
	name = p.xpath("./name")[0].text.split(">")[1].split("<")[0]
	netmon_id = p.xpath("./name")[0].text.split("=")[2].split("'")[0]
	(lng, lat, alt) = p.xpath("./Point/coordinates")[0].text.split(",")
	lat = float(lat)
	lng = float(lng)
	routers.insert_one({"name": name, "netmon_id": netmon_id, "position": {"lat": lat, "lng": lng}})
"""

interfaces_used_for_crawling = ["br-mesh", "br-client", "floh_fix", "tata_fix"]

"""
for router in routers.find({"bootstrap_ip": {"$exists": False}}):
	print("Crawling »%s«" % router["name"])
	page = requests.get("https://netmon.freifunk-franken.de/router.php", params={"router_id": router["netmon_id"]}).text
	if "br-client" in page:
		bootstrap_ip = "fe80%s" % page.split("<b>br-client</b>")[1].split("fe80")[1].split("/")[0]
		print("   IP: %s" % bootstrap_ip)
		routers.update_one({"_id": router["_id"]}, {"$set": {"bootstrap_ip": bootstrap_ip}})
	#time.sleep(0.2)
"""

for router in routers.find({"bootstrap_ip": {"$exists": True}}):
	if router["name"] != "Schoppershofstrasse51":
		continue
	node_data = subprocess.check_output(["curl", "-s", "--max-time", "10", "http://[%s%%wlan0]/node.data" % router["bootstrap_ip"]])
	try:
		node_data = gzip.decompress(node_data)
	except:
		pass
	print(router["name"])
	print(node_data)
	import sys; sys.exit(1)
