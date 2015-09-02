#!/usr/bin/python

import lxml.etree
import requests
import time
import subprocess
import gzip
from queue import Queue
from threading import Thread
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

CONFIG = {
	"crawl_netif": "br-mesh",
	"mac_netif": "br-mesh",
	"vpn_netif": "fffVPN",
	"crawl_outgoing_netif": "wlan0",
	"num_crawler_threads": 10
}

crawl_hood = "nuernberg"

def crawl(router):
	print("Crawling »%(hostname)s«" % router)
	crawl_ip = next(netif["ipv6_fe80_addr"] for netif in router["netifs"] if netif["name"] == CONFIG["crawl_netif"])
	try:
		node_data = subprocess.check_output(["curl", "-s", "--max-time", "5", "http://[%s%%%s]/node.data" % (
			crawl_ip,
			CONFIG["crawl_outgoing_netif"]
		)])
		try:
			node_data = gzip.decompress(node_data)
		except:
			pass

		assert "<TITLE>404" not in str(node_data).upper()

		tree = lxml.etree.fromstring(node_data)
		print(" --> " + tree.xpath("/data/system_data/hostname/text()")[0])

		router_update = {
			"status": tree.xpath("/data/system_data/status/text()")[0],
			"has_wan_uplink": len(tree.xpath("/data/interface_data/fffVPN")) > 0,
			"hostname": tree.xpath("/data/system_data/hostname/text()")[0],
			"neighbours": [], # list of mongoDB ids (or mac if no corresponding id found)
			"netifs": [],
		}

		for netif in tree.xpath("/data/interface_data/*"):
			interface = {
				"name": netif.xpath("name/text()")[0],
				"mtu": int(netif.xpath("mtu/text()")[0]),
				"mac": netif.xpath("mac_addr/text()")[0].lower(),
			}
			if len(netif.xpath("ipv6_link_local_addr/text()")) > 0:
				interface["ipv6_fe80_addr"] = netif.xpath("ipv6_link_local_addr/text()")[0].lower().split("/")[0]
			if len(netif.xpath("ipv4_addr/text()")) > 0:
				interface["ipv4_addr"] = netif.xpath("ipv4_addr/text()")[0]
			router_update["netifs"].append(interface)

		for originator in tree.xpath("/data/batman_adv_originators/*"):
			o_mac = originator.xpath("originator/text()")[0]
			o_nexthop = originator.xpath("nexthop/text()")[0]
			# mac is the mac of the neighbour w2/5mesh if
			# (which might also be called wlan0-1)
			o_link_quality = originator.xpath("link_quality/text()")[0]
			o_out_if = originator.xpath("outgoing_interface/text()")[0]
			if o_mac.upper() == o_nexthop.upper():
				# skip vpn server
				if o_out_if == CONFIG["vpn_netif"]:
					continue
				neighbour = {
					"mac": o_mac.lower(),
					"quality": int(o_link_quality),
					"net_if": o_out_if,
				}
				try:
					neighbour_router = db.routers.find_one({"netifs.mac": neighbour["mac"]})
					neighbour["_id"] = neighbour_router["_id"]
					assert "coordinates" in neighbour_router["position"]
					assert neighbour_router["position"]["coordinates"][0] != 0
					assert neighbour_router["position"]["coordinates"][1] != 0
					if "comment" in neighbour_router["position"]:
						del neighbour_router["position"]["comment"]
					neighbour["position"] = neighbour_router["position"]
				except:
					pass
				router_update["neighbours"].append(neighbour)

		db.routers.update_one({"_id": router["_id"]}, {"$set": router_update})

		#from pprint import pprint
		#pprint(router)
	except subprocess.CalledProcessError:
		db.routers.update_one({"_id": router["_id"]}, {"$set": {"status": "offline"}})
		print(" --> OFFLINE")
	except AssertionError:
		db.routers.update_one({"_id": router["_id"]}, {"$set": {"status": "unknown"}})
		print(" --> UNKNOWN")

q = Queue()
keep_working = True

def worker():
	while keep_working:
		router = q.get()
		crawl(router)
		q.task_done()

for i in range(CONFIG["num_crawler_threads"]):
	t = Thread(target=worker)
	t.daemon = True
	t.start()

for router in db.routers.find({"netifs.name": CONFIG["crawl_netif"], "hood": crawl_hood}):
	q.put(router)

# block until queue is empty
q.join()

# stop workers
keep_working = False
