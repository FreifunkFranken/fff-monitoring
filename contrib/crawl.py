#!/usr/bin/python

import lxml.etree
import requests
import time
import subprocess
import gzip
import datetime
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
			"hostname": tree.xpath("/data/system_data/hostname/text()")[0],
			"neighbours": [],
			"netifs": [],
			"system": {
				"time": datetime.datetime.fromtimestamp(int(tree.xpath("/data/system_data/local_time/text()")[0])),
				"uptime": int(float(tree.xpath("/data/system_data/uptime/text()")[0])),
				"memory": {
					"free": int(tree.xpath("/data/system_data/memory_free/text()")[0]),
					"buffering": int(tree.xpath("/data/system_data/memory_buffering/text()")[0]),
					"caching": int(tree.xpath("/data/system_data/memory_caching/text()")[0]),
				},
				"loadavg": float(tree.xpath("/data/system_data/loadavg/text()")[0]),
				"processes": {
					"runnable": int(tree.xpath("/data/system_data/processes/text()")[0].split("/")[0]),
					"total": int(tree.xpath("/data/system_data/processes/text()")[0].split("/")[1]),
				},
				"clients": int(tree.xpath("/data/client_count/text()")[0]),
				"has_wan_uplink": len(tree.xpath("/data/interface_data/fffVPN")) > 0,
			},
			"hardware": {
				"chipset": tree.xpath("/data/system_data/chipset/text()")[0],
				"cpu": tree.xpath("/data/system_data/cpu/text()")[0]
			},
			"software": {
				"os": "%s (%s)" % (tree.xpath("/data/system_data/distname/text()")[0],
				                   tree.xpath("/data/system_data/distversion/text()")[0]),
				"batman_adv": tree.xpath("/data/system_data/batman_advanced_version/text()")[0],
				"kernel": tree.xpath("/data/system_data/kernel_version/text()")[0],
				"nodewatcher": tree.xpath("/data/system_data/nodewatcher_version/text()")[0],
				#"fastd": tree.xpath("/data/system_data/fastd_version/text()")[0],
				"firmware": tree.xpath("/data/system_data/firmware_version/text()")[0],
				"firmware_rev": tree.xpath("/data/system_data/firmware_revision/text()")[0],
			}
		}

		# get hardware.name by chipset
		chipset = db.chipsets.find_one({"name": router_update["hardware"]["chipset"]})
		if chipset:
			router_update["hardware"]["name"] = chipset["hardware"]
		else:
			print("Unknown Chipset: %s" % router_update["hardware"]["chipset"])

		for netif in tree.xpath("/data/interface_data/*"):
			interface = {
				"name": netif.xpath("name/text()")[0],
				"mtu": int(netif.xpath("mtu/text()")[0]),
				"mac": netif.xpath("mac_addr/text()")[0].lower(),
				"traffic": {
					"rx": int(netif.xpath("traffic_rx/text()")[0]),
					"tx": int(netif.xpath("traffic_tx/text()")[0]),
				},
			}
			if len(netif.xpath("ipv6_link_local_addr/text()")) > 0:
				interface["ipv6_fe80_addr"] = netif.xpath("ipv6_link_local_addr/text()")[0].lower().split("/")[0]
			if len(netif.xpath("ipv4_addr/text()")) > 0:
				interface["ipv4_addr"] = netif.xpath("ipv4_addr/text()")[0]
			router_update["netifs"].append(interface)

		visible_neighbours = 0

		for originator in tree.xpath("/data/batman_adv_originators/*"):
			visible_neighbours += 1
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
					"netif": o_out_if,
					"quality": int(o_link_quality),
				}
				try:
					neighbour_router = db.routers.find_one({"netifs.mac": neighbour["mac"]})
					neighbour["_id"] = neighbour_router["_id"]
					neighbour["hostname"] = neighbour_router["hostname"]
					assert "coordinates" in neighbour_router["position"]
					assert neighbour_router["position"]["coordinates"][0] != 0
					assert neighbour_router["position"]["coordinates"][1] != 0
					if "comment" in neighbour_router["position"]:
						del neighbour_router["position"]["comment"]
					neighbour["position"] = neighbour_router["position"]
				except:
					pass
				router_update["neighbours"].append(neighbour)

		router_update["system"]["visible_neighbours"] = visible_neighbours

		db.routers.update_one({"_id": router["_id"]}, {"$set": router_update, "$currentDate": {"last_contact": True}})
		status = router_update["status"]
	except subprocess.CalledProcessError:
		# in a non-crawling setup the system would need to
		# mark routers as offline when the last_contact is too far in the past
		# eg by a cronjob
		db.routers.update_one({"_id": router["_id"]}, {"$set": {"status": "offline"}})
		status = "offline"
		print(" --> OFFLINE")
	except (AssertionError, lxml.etree.XMLSyntaxError):
		db.routers.update_one({"_id": router["_id"]}, {"$set": {"status": "unknown"}})
		status = "unknown"
		print(" --> UNKNOWN")
	finally:
		# fire events
		events = []
		try:
			if router["system"]["uptime"] > router_update["system"]["uptime"]:
				events.append({
					"time": datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc),
					"type": "reboot",
				})
		except:
			pass
		if router["status"] != status:
			events.append({
				"time": datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc),
				"type": status,
			})
		db.routers.update_one({"_id": router["_id"]}, {"$push": {"events": {
			"$each": events,
			"$slice": -10,
		}}})

	if status == "online":
		# calculate RRD statistics
		#FIXME: implementation
		pass


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
