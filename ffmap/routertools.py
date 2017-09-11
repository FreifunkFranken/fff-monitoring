#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.dbtools import FreifunkDB
from ffmap.misc import *

import lxml.etree
import datetime
import requests
from bson import SON
from contextlib import suppress

db = FreifunkDB().handle()

CONFIG = {
	"vpn_netif": "fffVPN",
	"vpn_netif_l2tp": "l2tp",
	"vpn_netif_aux": "fffauxVPN",
	"offline_threshold_minutes": 20,
	"orphan_threshold_days": 120,
	"router_stat_days": 7,
}

router_rate_limit_list = {}

def import_nodewatcher_xml(mac, xml):
	global router_rate_limit_list

	t = utcnow()
	if mac in router_rate_limit_list:
		if (t - router_rate_limit_list[mac]) < datetime.timedelta(minutes=5):
			return
	router_rate_limit_list[mac] = t

	router_id = None
	events = []
	try:
		router = db.routers.find_one({"netifs.mac": mac.lower()}, {"stats": 0, "events": 0})
		if router:
			router_id = router["_id"]

		router_update = parse_nodewatcher_xml(xml)

		# keep hood up to date
		if not "hood" in router_update:
			# router didn't send his hood in XML
			if "position" in router_update:
				# router has new position info from netmon
				router_update["hood"] = db.hoods.find_one({"position": {"$near": {"$geometry": router_update["position"]}}})["name"]
			elif router and "position" in router:
				# hoods might change as well
				router_update["hood"] = db.hoods.find_one({"position": {"$near": {"$geometry": router["position"]}}})["name"]

		if router:
			# statistics
			calculate_network_io(router, router_update)
			db.routers.update_one({"_id": router_id}, {
				"$set": router_update,
				"$push": {"stats": SON([
					("$each", new_router_stats(router, router_update)),
					("$slice", int(CONFIG["router_stat_days"] * -1 * 24 * (3600 / 300)))
				])
			}})
		else:
			# insert new router
			router_update["created"] = utcnow()
			router_update["stats"] = []
			events = [] # don't fire sub-events of created events
			router_update["events"] = [{
				"time": utcnow(),
				"type": "created",
			}]
			router_id = db.routers.insert_one(router_update).inserted_id
		status = router_update["status"]
	except ValueError as e:
		import traceback
		print("Warning: Unable to parse xml from %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router:
			db.routers.update_one({"_id": router_id}, {"$set": {
				"status": "unknown",
				"last_contact": utcnow()
			}})
		status = "unknown"
		status_comment = "Invalid XML"
	except OverflowError as e:
		import traceback
		print("Warning: Overflow Error when saving %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router:
			db.routers.update_one({"_id": router_id}, {"$set": {
				"status": "unknown",
				"last_contact": utcnow()
			}})
		status = "unknown"
		status_comment = "Integer Overflow"
	except Exception as e:
		import traceback
		print("Warning: Exception occurred when saving %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router:
			db.routers.update_one({"_id": router_id}, {"$set": {
				"status": "unknown",
				"last_contact": utcnow()
			}})
		status = "unknown"
		status_comment = "Exception occurred"

	if router_id:
		# fire events
		with suppress(KeyError, TypeError, UnboundLocalError):
			if router["system"]["uptime"] > router_update["system"]["uptime"]:
				events.append({
					"time": utcnow(),
					"type": "reboot",
				})

		with suppress(KeyError, TypeError, UnboundLocalError):
			if router["software"]["firmware"] != router_update["software"]["firmware"]:
				events.append({
					"time": utcnow(),
					"type": "update",
					"comment": "%s -> %s" % (router["software"]["firmware"], router_update["software"]["firmware"]),
				})

		with suppress(KeyError, TypeError, UnboundLocalError):
			if router["hostname"] != router_update["hostname"]:
				events.append({
					"time": utcnow(),
					"type": "hostname",
					"comment": "%s -> %s" % (router["hostname"], router_update["hostname"]),
				})

		with suppress(KeyError, TypeError, UnboundLocalError):
			if router["hood"] != router_update["hood"]:
				events.append({
					"time": utcnow(),
					"type": "hood",
					"comment": "%s -> %s" % (router["hood"], router_update["hood"]),
				})

		with suppress(KeyError, TypeError):
			if router["status"] != status:
				event = {
					"time": utcnow(),
					"type": status,
				}
				with suppress(NameError):
					event["comment"] = status_comment
				events.append(event)

		if len(events) > 0:
			db.routers.update_one({"_id": router_id}, {"$push": {"events": SON([
				("$each", events),
				("$slice", -10),
			])}})

def detect_offline_routers():
	db.routers.update_many({
		"last_contact": {"$lt": utcnow() - datetime.timedelta(minutes=CONFIG["offline_threshold_minutes"])},
		"status": {"$ne": "offline"}
	}, {
		"$set": {"status": "offline", "system.clients": 0},
		"$push": {"events": {
			"time": utcnow(),
			"type": "offline"
		}
	}})

def delete_orphaned_routers():
	db.routers.delete_many({
		"last_contact": {"$lt": utcnow() - datetime.timedelta(days=CONFIG["orphan_threshold_days"])},
		"status": "offline"
	})

def new_router_stats(router, router_update):
	if router["system"]["uptime"] < router_update["system"]["uptime"]:
		netifs = {}
		neighbours = {}
		for netif in router_update["netifs"]:
			# sanitize name
			name = netif["name"].replace(".", "").replace("$", "")
			with suppress(KeyError):
				netifs[name] = {"rx": netif["traffic"]["rx"], "tx": netif["traffic"]["tx"]}
		for neighbour in router_update["neighbours"]:
			with suppress(KeyError):
				neighbours[neighbour["mac"]] = neighbour["quality"]
		return [{
			"time": utcnow(),
			"netifs": netifs,
			"neighbours": neighbours,
			"memory": router_update["system"]["memory"],
			"loadavg": router_update["system"]["loadavg"],
			"processes": router_update["system"]["processes"],
			"clients": router_update["system"]["clients"],
		}]
	else:
		# don't push old data
		return []

def calculate_network_io(router, router_update):
	"""
	router: old router dict
	router_update: new router dict (which will be updated with new data)
	"""
	with suppress(KeyError, StopIteration):
		if router["system"]["uptime"] < router_update["system"]["uptime"]:
			timediff =  router_update["system"]["uptime"] - router["system"]["uptime"]
			for netif in router["netifs"]:
				netif_update = next(filter(lambda n: n["name"] == netif["name"], router_update["netifs"]))
				rx_diff = netif_update["traffic"]["rx_bytes"] - netif["traffic"]["rx_bytes"]
				tx_diff = netif_update["traffic"]["tx_bytes"] - netif["traffic"]["tx_bytes"]
				if rx_diff >= 0 and tx_diff >= 0:
					netif_update["traffic"]["rx"] = int(rx_diff / timediff)
					netif_update["traffic"]["tx"] = int(tx_diff / timediff)
		else:
			for netif in router["netifs"]:
				netif_update = next(filter(lambda n: n["name"] == netif["name"], router_update["netifs"]))
				netif_update["traffic"]["rx"] = netif["traffic"]["rx"]
				netif_update["traffic"]["tx"] = netif["traffic"]["tx"]

def parse_nodewatcher_xml(xml):
	try:
		assert xml != ""
		tree = lxml.etree.fromstring(xml)

		router_update = {
			"status": tree.xpath("/data/system_data/status/text()")[0],
			"hostname": tree.xpath("/data/system_data/hostname/text()")[0],
			"last_contact": utcnow(),
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
				"has_wan_uplink": (
					(len(tree.xpath("/data/system_data/vpn_active")) > 0
					and int(tree.xpath("/data/system_data/vpn_active/text()")[0]) == 1)
					or len(tree.xpath("/data/interface_data/%s" % CONFIG["vpn_netif"])) > 0
					or len(tree.xpath("/data/interface_data/*[starts-with(name(), '%s')]" % CONFIG["vpn_netif_l2tp"])) > 0
					or len(tree.xpath("/data/interface_data/%s" % CONFIG["vpn_netif_aux"])) > 0),
			},
			"hardware": {
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

		# data.system_data.chipset
		with suppress(IndexError):
			router_update["hardware"]["chipset"] = "Unknown"
			router_update["hardware"]["chipset"] = tree.xpath("/data/system_data/chipset/text()")[0]

		# data.system_data.model
		with suppress(IndexError):
			router_update["hardware"]["name"] = "Legacy"
			router_update["hardware"]["name"] = tree.xpath("/data/system_data/model/text()")[0]

		# data.system_data.chipset
		with suppress(IndexError):
			router_update["hardware"]["chipset"] = "Unknown"
			router_update["hardware"]["chipset"] = tree.xpath("/data/system_data/chipset/text()")[0]

		# data.system_data.description
		with suppress(IndexError):
			router_update["description"] = tree.xpath("/data/system_data/description/text()")[0]

		# data.system_data.position_comment
		with suppress(IndexError):
			router_update["position_comment"] = tree.xpath("/data/system_data/position_comment/text()")[0]

		# data.system_data.firmware_community
		with suppress(IndexError):
			router_update["community"] = tree.xpath("/data/system_data/firmware_community/text()")[0]

		# data.system_data.hood
		with suppress(IndexError):
			router_update["hood"] = tree.xpath("/data/system_data/hood/text()")[0].lower()

		# data.system_data.status_text
		with suppress(IndexError):
			router_update["system"]["status_text"] = tree.xpath("/data/system_data/status_text/text()")[0]

		# data.system_data.contact
		with suppress(IndexError):
			router_update["system"]["contact"] = tree.xpath("/data/system_data/contact/text()")[0]
			user = db.users.find_one({"email": router_update["system"]["contact"]})
			if user:
				# post-netmon router gets its user assigned
				router_update["user"] = {"nickname": user["nickname"], "_id": user["_id"]}

		# data.system_data.geo
		with suppress(AssertionError, IndexError):
			lng = float(tree.xpath("/data/system_data/geo/lng/text()")[0])
			lat = float(tree.xpath("/data/system_data/geo/lat/text()")[0])
			assert lng != 0
			assert lat != 0

			router_update["position"] = {
				"type": "Point",
				"coordinates": [lng, lat]
			}

		#FIXME: tmp workaround to get similar hardware names
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("nanostation-m", "Ubiquiti Nanostation M")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr1043nd-v1", "TP-Link TL-WR1043N/ND v1")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr1043nd-v2", "TP-Link TL-WR1043N/ND v2")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr741nd-v2", "TP-Link TL-WR741N/ND v2")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr741nd-v4", "TP-Link TL-WR741N/ND v4")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr841nd-v7", "TP-Link TL-WR841N/ND v7")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr841n-v8", "TP-Link TL-WR841N/ND v8")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr841n-v9", "TP-Link TL-WR841N/ND v9")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr841nd-v9", "TP-Link TL-WR841N/ND v9")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wr842n-v2", "TP-Link TL-WR842N/ND v2")
		router_update["hardware"]["name"] = router_update["hardware"]["name"].replace("tl-wdr4300", "TP-Link TL-WDR4300")

		for netif in tree.xpath("/data/interface_data/*"):
			interface = {
				"name": netif.xpath("name/text()")[0],
				"mtu": int(netif.xpath("mtu/text()")[0]),
				"traffic": {
					"rx_bytes": int(netif.xpath("traffic_rx/text()")[0]),
					"tx_bytes": int(netif.xpath("traffic_tx/text()")[0]),
				},
			}
			with suppress(IndexError):
				interface["ipv6_fe80_addr"] = netif.xpath("ipv6_link_local_addr/text()")[0].lower().split("/")[0]
			if len(netif.xpath("ipv6_addr/text()")) > 0:
				interface["ipv6_addrs"] = []
				for ipv6_addr in netif.xpath("ipv6_addr/text()"):
					interface["ipv6_addrs"].append(ipv6_addr.lower().split("/")[0])
			with suppress(IndexError):
				interface["ipv4_addr"] = netif.xpath("ipv4_addr/text()")[0]

			with suppress(IndexError):
				interface["mac"] = ""
				interface["mac"] = netif.xpath("mac_addr/text()")[0].lower()
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
				elif o_out_if.startswith(CONFIG["vpn_netif_l2tp"]):
					continue
				elif o_out_if == CONFIG["vpn_netif_aux"]:
					continue
				neighbour = {
					"mac": o_mac.lower(),
					"quality": int(o_link_quality),
					"net_if": o_out_if,
				}
				set_hostname_and_pos_for_neighbour(neighbour)
				router_update["neighbours"].append(neighbour)

		l3_neighbours = get_l3_neighbours(tree)
		visible_neighbours += len(l3_neighbours)
		router_update["system"]["visible_neighbours"] = visible_neighbours
		router_update["neighbours"] += l3_neighbours

		return router_update
	except (AssertionError, lxml.etree.XMLSyntaxError, IndexError) as e:
		raise ValueError("%s: %s" % (e.__class__.__name__, str(e)))


def set_hostname_and_pos_for_neighbour(neighbour):
	with suppress(AssertionError, TypeError):
		neighbour_router = db.routers.find_one(
			{"netifs.mac": neighbour["mac"]}, {"hostname": 1, "position": 1})
		neighbour["_id"] = neighbour_router["_id"]
		neighbour["hostname"] = neighbour_router["hostname"]
		assert "position" in neighbour_router
		assert "coordinates" in neighbour_router["position"]
		assert neighbour_router["position"]["coordinates"][0] != 0
		assert neighbour_router["position"]["coordinates"][1] != 0
		neighbour["position"] = neighbour_router["position"]


def get_l3_neighbours(tree):
	l3_neighbours = list()
	for neighbour in tree.xpath("/data/babel_neighbours/*"):
		v6_fe80 = neighbour.text
		out_if = neighbour.xpath("outgoing_interface/text()")[0]
		neighbour = {
			"mac": get_mac_from_v6_link_local(v6_fe80).lower(),
			"quality": -1,
			"net_if": out_if,
			"type": "l3"
		}
		set_hostname_and_pos_for_neighbour(neighbour)
		l3_neighbours.append(neighbour)
	return l3_neighbours


def get_mac_from_v6_link_local(v6_fe80):
	v6_fe80_parts = v6_fe80[6:].split(':')
	mac = list()
	for v6_fe80_part in v6_fe80_parts:
		while len(v6_fe80_part) < 4:
			v6_fe80_part = '0' + v6_fe80_part
		mac.append(v6_fe80_part[:2])
		mac.append(v6_fe80_part[-2:])

	mac[0] = '%02x' % (int(mac[0], 16) ^ 2)
	del mac[3]
	del mac[3]

	return ':'.join(mac)
