#!/usr/bin/python

import netmon

import lxml.etree
import datetime
from pymongo import MongoClient

client = MongoClient()
db = client.freifunk

CONFIG = {
	"vpn_netif": "fffVPN",
}

def process_router_xml(mac, xml):
	try:
		router = db.routers.find_one({"netifs.mac": mac.lower()})
		if router:
			router_id = router["_id"]

		assert xml != ""
		tree = lxml.etree.fromstring(xml)

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

		# get hardware.name by chipset - FIXME: this should be found out by nodewatcher
		chipset = db.chipsets.find_one({"name": router_update["hardware"]["chipset"]})
		if chipset:
			router_update["hardware"]["name"] = chipset["hardware"]

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

		if router:
			# keep hood up to date
			router_update["hood"] = db.hoods.find_one({"position": {"$near": {"$geometry": router["position"]}}})["name"]
			db.routers.update_one({"netifs.mac": mac.lower()}, {"$set": router_update, "$currentDate": {"last_contact": True}})
		else:
			# new router
			# fetch additional information from netmon as it is not yet contained in xml
			router_info = netmon.fetch_router_info(mac)
			if router_info:
				# keep hood up to date
				router_update["hood"] = db.hoods.find_one({"position": {"$near": {"$geometry": router_info["position"]}}})["name"]
				router_update.update(router_info)
			router_id = db.routers.insert_one(router_update).inserted_id
		status = router_update["status"]
	except (AssertionError, lxml.etree.XMLSyntaxError):
		if router:
			db.routers.update_one({"_id": router_id}, {"$set": {"status": "unknown"}})
		status = "unknown"
	finally:
		# fire events
		events = []
		try:
			if not router:
				events.append({
					"time": datetime.datetime.utcnow(),
					"type": "created",
				})
		except:
			pass
		try:
			if router["system"]["uptime"] > router_update["system"]["uptime"]:
				events.append({
					"time": datetime.datetime.utcnow(),
					"type": "reboot",
				})
		except:
			pass
		try:
			if router["status"] != status:
				events.append({
					"time": datetime.datetime.utcnow(),
					"type": status,
				})
		except:
			pass
		db.routers.update_one({"_id": router_id}, {"$push": {"events": {
			"$each": events,
			"$slice": -10,
		}}})

	if status == "online":
		# calculate RRD statistics (rrdcache?)
		#FIXME: implementation
		pass
