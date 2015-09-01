#!/usr/bin/python

import lxml.etree
import sys
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk
routers = db.routers

routervpnif = "fffVPN"

# usage: $0 CRAWL_XML_FILE

tree = lxml.etree.parse(sys.argv[1])

# if request fails --> status offline

router = {
	"status": "online",
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
	router["netifs"].append(interface)


for originator in tree.xpath("/data/batman_adv_originators/*"):
	o_mac = originator.xpath("originator/text()")[0]
	o_nexthop = originator.xpath("nexthop/text()")[0]
	# mac is the mac of the neighbour w2/5mesh if
	# (which might also be called wlan0-1)
	o_link_quality = originator.xpath("link_quality/text()")[0]
	o_out_if = originator.xpath("outgoing_interface/text()")[0]
	if o_mac.upper() == o_nexthop.upper():
		# skip vpn server
		if o_out_if == routervpnif:
			continue
		neighbour = {
			"mac": o_mac.lower(),
			"quality": int(o_link_quality),
			"net_if": o_out_if,
		}
		try:
			neighbour["_id"] = routers.find_one({"netifs.mac": neighbour["mac"]})["_id"]
		except:
			pass
		router["neighbours"].append(neighbour)

routers.update_one({"name": router["hostname"]}, {"$set": router})

from pprint import pprint
pprint(router)
