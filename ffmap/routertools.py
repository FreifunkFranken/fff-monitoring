#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.dbtools import FreifunkDB

import lxml.etree
import datetime
import requests
from bson import SON
from contextlib import suppress

db = FreifunkDB().handle()

CONFIG = {
	"vpn_netif": "fffVPN",
}

def import_nodewatcher_xml(mac, xml):
	try:
		router = db.routers.find_one({"netifs.mac": mac.lower()})
		if router:
			router_id = router["_id"]

		router_update = parse_nodewatcher_xml(xml)

		if router and "netmon_id" in router:
			# router is already in db and initial netmon data fetch was successfull
			# keep hood up to date
			if "position" in router:
				router_update["hood"] = db.hoods.find_one({"position": {"$near": {"$geometry": router["position"]}}})["name"]
		else:
			# new router
			# fetch additional information from netmon as it is not yet contained in xml
			router_info = netmon_fetch_router_info(mac)
			if router_info:
				# keep hood up to date
				if "position" in router_info:
					router_update["hood"] = db.hoods.find_one({"position": {"$near": {"$geometry": router_info["position"]}}})["name"]
				router_update["events"] = [{
					"time": datetime.datetime.utcnow(),
					"type": "created",
				}]
				router_update.update(router_info)

		if router:
			# statistics
			calculate_network_io(router, router_update)
			db.routers.update_one({"netifs.mac": mac.lower()}, {
				"$set": router_update,
				"$push": {"stats": SON([
					("$each", new_router_stats(router, router_update)),
					("$slice", -8640)
				])
			}})
		else:
			router_id = db.routers.insert_one(router_update).inserted_id
		status = router_update["status"]
	except ValueError:
		if router:
			db.routers.update_one({"_id": router_id}, {"$set": {"status": "unknown"}})
		status = "unknown"

	if router_id:
		# fire events
		events = []
		with suppress(KeyError, TypeError):
			if router["system"]["uptime"] > router_update["system"]["uptime"]:
				events.append({
					"time": datetime.datetime.utcnow(),
					"type": "reboot",
				})

		with suppress(KeyError, TypeError):
			if router["software"]["firmware"] != router_update["software"]["firmware"]:
				events.append({
					"time": datetime.datetime.utcnow(),
					"type": "update",
					"comment": "%s -> %s" % (router["software"]["firmware"], router_update["software"]["firmware"]),
				})

		with suppress(KeyError, TypeError):
			if router["status"] != status:
				events.append({
					"time": datetime.datetime.utcnow(),
					"type": status,
				})

		if len(events) > 0:
			db.routers.update_one({"_id": router_id}, {"$push": {"events": SON([
				("$each", events),
				("$slice", -10),
			])}})

def detect_offline_routers():
	db.routers.update_many({
		"last_contact": {"$lt": datetime.datetime.utcnow() - datetime.timedelta(minutes=10)},
		"status": {"$ne": "offline"}
	}, {
		"$set": {"status": "offline"},
		"$push": {"events": {
			"time": datetime.datetime.utcnow(),
			"type": "offline"
		}
	}})

def new_router_stats(router, router_update):
	if router["system"]["uptime"] < router_update["system"]["uptime"]:
		netifs = {}
		for netif in router_update["netifs"]:
			# sanitize name
			name = netif["name"].replace(".", "").replace("$", "")
			with suppress(KeyError):
				netifs[name] = {"rx": netif["traffic"]["rx"], "tx": netif["traffic"]["tx"]}
		return [{
			"time": datetime.datetime.utcnow(),
			"netifs": netifs,
			"memory": router_update["system"]["memory"],
			"processes": router_update["system"]["processes"],
			"clients": router_update["system"]["clients"],
		}]
	else:
		# don't push old data
		return []

def calculate_network_io(router, router_update):
	"""
	router: old router dict
	router: new router dict (which will be updated with new data)
	"""
	try:
		if router["system"]["uptime"] < router_update["system"]["uptime"]:
			timediff =  router_update["system"]["uptime"] - router["system"]["uptime"]
			for netif in router["netifs"]:
				netif_update = next(filter(lambda n: n["name"] == netif["name"], router_update["netifs"]))
				rx_diff = netif_update["traffic"]["rx_bytes"] - netif["traffic"]["rx_bytes"]
				tx_diff = netif_update["traffic"]["tx_bytes"] - netif["traffic"]["tx_bytes"]
				if rx_diff > 0 and tx_diff > 0:
					netif_update["traffic"]["rx"] = int(rx_diff / timediff)
					netif_update["traffic"]["tx"] = int(tx_diff / timediff)
		else:
			for netif in router["netifs"]:
				netif_update = next(filter(lambda n: n["name"] == netif["name"], router_update["netifs"]))
				netif_update["traffic"]["rx"] = netif["traffic"]["rx"]
				netif_update["traffic"]["tx"] = netif["traffic"]["tx"]
	except (KeyError, StopIteration):
		pass

def parse_nodewatcher_xml(xml):
	try:
		assert xml != ""
		tree = lxml.etree.fromstring(xml)

		router_update = {
			"status": tree.xpath("/data/system_data/status/text()")[0],
			"hostname": tree.xpath("/data/system_data/hostname/text()")[0],
			"last_contact": datetime.datetime.utcnow(),
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
				"name": tree.xpath("/data/system_data/model/text()")[0].upper(),
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

		for netif in tree.xpath("/data/interface_data/*"):
			interface = {
				"name": netif.xpath("name/text()")[0],
				"mtu": int(netif.xpath("mtu/text()")[0]),
				"mac": netif.xpath("mac_addr/text()")[0].lower(),
				"traffic": {
					"rx_bytes": int(netif.xpath("traffic_rx/text()")[0]),
					"tx_bytes": int(netif.xpath("traffic_tx/text()")[0]),
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
					"quality": int(o_link_quality),
					"net_if": o_out_if,
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

		return router_update
	except (AssertionError, lxml.etree.XMLSyntaxError) as e:
		raise ValueError("%s: %s" % (e.__class__.__name__, e.msg))

def netmon_fetch_router_info(mac):
	mac = mac.replace(":", "").lower()
	tree = lxml.etree.fromstring(requests.get("https://netmon.freifunk-franken.de/api/rest/router/%s" % mac, params={"limit": 5000}).content)

	for r in tree.xpath("/netmon_response/router"):
		user_netmon_id = int(r.xpath("user_id/text()")[0])
		user = db.users.find_one({"netmon_id": user_netmon_id})
		if user:
			user_id = user["_id"]
		else:
			user_id = db.users.insert({
				"netmon_id": user_netmon_id,
				"nickname": r.xpath("user/nickname/text()")[0]
			})
			user = db.users.find_one({"_id": user_id})

		router = {
			"netmon_id": int(r.xpath("router_id/text()")[0]),
			"user": {"nickname": user["nickname"], "_id": user["_id"]}
		}

		try:
			lng = float(r.xpath("longitude/text()")[0])
			lat = float(r.xpath("latitude/text()")[0])
			assert lng != 0
			assert lat != 0

			router["position"] = {
				"type": "Point",
				"coordinates": [lng, lat]
			}

			# try to get comment
			position_comment = r.xpath("location/text()")[0]
			if position_comment != "undefined":
				router["position"]["comment"] = position_comment
		except (IndexError, AssertionError):
			pass

		try:
			router["description"] = r.xpath("description/text()")[0]
		except IndexError:
			pass

		router["created"] = datetime.datetime.utcnow()

		return router
