#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL
from ffmap.misc import *

import lxml.etree
import datetime
import requests
from bson import SON
from contextlib import suppress

CONFIG = {
	"vpn_netif": "fffVPN",
	"vpn_netif_l2tp": "l2tp",
	"vpn_netif_aux": "fffauxVPN",
	"offline_threshold_minutes": 20,
	"orphan_threshold_days": 120,
	"router_stat_days": 7,
}

router_rate_limit_list = {}

def delete_router(mysql,dbid):
	cur = mysql.cursor()
	cur.execute("DELETE FROM router WHERE id = %s",(dbid,))
	cur.execute("DELETE FROM router_netif WHERE router = %s",(dbid,))
	cur.execute("DELETE FROM router_ipv6 WHERE router = %s",(dbid,))
	cur.execute("DELETE FROM router_neighbor WHERE router = %s",(dbid,))
	cur.execute("DELETE FROM router_events WHERE router = %s",(dbid,))
	cur.execute("DELETE FROM router_stats WHERE router = %s",(dbid,))
	cur.execute("DELETE FROM router_stats_neighbor WHERE router = %s",(dbid,))
	cur.execute("DELETE FROM router_stats_netif WHERE router = %s",(dbid,))
	mysql.commit()

def import_nodewatcher_xml(mysql, mac, xml):
	global router_rate_limit_list

	cur = mysql.cursor()

	t = utcnow()
	if mac in router_rate_limit_list:
		if (t - router_rate_limit_list[mac]) < datetime.timedelta(minutes=5):
			return
	router_rate_limit_list[mac] = t

	router_id = None
	olddata = []
	uptime = 0
	events = []
	status_comment = ""
	
	try:
		cur.execute("SELECT router FROM router_netif WHERE mac = %s LIMIT 1",(mac.lower(),))
		result = cur.fetchall()
		if len(result)>0:
			router_id = result[0]["router"]
			cur.execute("SELECT sys_uptime AS uptime, firmware, hostname, hood, status, lat, lng FROM router WHERE id = %s LIMIT 1",(router_id,))
			result = cur.fetchall()
			if len(result)>0:
				olddata = result[0]
				uptime = olddata["uptime"]
		router_update = parse_nodewatcher_xml(xml)

		# keep hood up to date
		if not router_update["hood"]:
			# router didn't send his hood in XML
			lat = router_update.get("lat")
			lng = router_update.get("lng")
			if olddata and not lat and not lng:
				# hoods might change as well
				lat = olddata.get("lat")
				lng = olddata.get("lng")
			if lat and lng:
				router_update["hood"] = mysql.findone("""
					SELECT name,
						( acos(  cos( radians(%s) )
									  * cos_lat
									  * cos( radians( lng ) - radians(%s) )
									  + sin( radians(%s) ) * sin_lat
									 )
						) AS distance
					FROM
						hoods
					WHERE lat IS NOT NULL AND lng IS NOT NULL
					ORDER BY
						distance ASC
					LIMIT 1
				""",(lat,lng,lat,),"name")
			else:
				router_update["hood"] = None
		
		if router_id:
			# statistics
			calculate_network_io(cur, router_id, uptime, router_update)
			ru = router_update
			rus = router_update["system"]
			ruh = router_update["hardware"]
			ruso = router_update["software"]
			cur.execute("""
				UPDATE router
				SET status = %s, hostname = %s, last_contact = %s, sys_time = %s, sys_uptime = %s, sys_memfree = %s, sys_membuff = %s, sys_memcache = %s,
				sys_loadavg = %s, sys_procrun = %s, sys_proctot = %s, clients = %s, wan_uplink = %s, cpu = %s, chipset = %s, hardware = %s, os = %s,
				batman = %s, kernel = %s, nodewatcher = %s, firmware = %s, firmware_rev = %s, description = %s, position_comment = %s, community = %s, hood = %s,
				status_text = %s, contact = %s, lng = %s, lat = %s, neighbors = %s
				WHERE id = %s
			""",(
				ru["status"],ru["hostname"],ru["last_contact"],rus["time"],rus["uptime"],rus["memory"]["free"],rus["memory"]["buffering"],rus["memory"]["caching"],
				rus["loadavg"],rus["processes"]["runnable"],rus["processes"]["total"],rus["clients"],rus["has_wan_uplink"],ruh["cpu"],ruh["chipset"],ruh["name"],ruso["os"],
				ruso["batman_adv"],ruso["kernel"],ruso["nodewatcher"],ruso["firmware"],ruso["firmware_rev"],ru["description"],ru["position_comment"],ru["community"],ru["hood"],
				ru["system"]["status_text"],ru["system"]["contact"],ru["lng"],ru["lat"],rus["visible_neighbours"],router_id,))
			
			cur.execute("DELETE FROM router_netif WHERE router = %s",(router_id,))
			cur.execute("DELETE FROM router_ipv6 WHERE router = %s",(router_id,))
			cur.execute("DELETE FROM router_neighbor WHERE router = %s",(router_id,))
			
			uptime = 0
			new_router_stats(mysql, router_id, uptime, router_update)
		else:
			# insert new router
			created = mysql.utcnow()
			#events = [] # don't fire sub-events of created events
			#router_update["events"] = [{
			#	"time": utcnow(),
			#	"type": "created",
			#}]
			ru = router_update
			rus = router_update["system"]
			ruh = router_update["hardware"]
			ruso = router_update["software"]
			
			cur.execute("""
				INSERT INTO router (status, hostname, created, last_contact, sys_time, sys_uptime, sys_memfree, sys_membuff, sys_memcache,
				sys_loadavg, sys_procrun, sys_proctot, clients, wan_uplink, cpu, chipset, hardware, os,
				batman, kernel, nodewatcher, firmware, firmware_rev, description, position_comment, community, hood,
				status_text, contact, lng, lat, neighbors)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""",(
				ru["status"],ru["hostname"],created,ru["last_contact"],rus["time"],rus["uptime"],rus["memory"]["free"],rus["memory"]["buffering"],rus["memory"]["caching"],
				rus["loadavg"],rus["processes"]["runnable"],rus["processes"]["total"],rus["clients"],rus["has_wan_uplink"],ruh["cpu"],ruh["chipset"],ruh["name"],ruso["os"],
				ruso["batman_adv"],ruso["kernel"],ruso["nodewatcher"],ruso["firmware"],ruso["firmware_rev"],ru["description"],ru["position_comment"],ru["community"],ru["hood"],
				ru["system"]["status_text"],ru["system"]["contact"],ru["lng"],ru["lat"],rus["visible_neighbours"],))
			router_id = cur.lastrowid
			
			events_append(mysql,router_id,"created","")
		
		for n in router_update["netifs"]:
			cur.execute("""
				INSERT INTO router_netif (router, netif, mtu, rx_bytes, tx_bytes, rx, tx, fe80_addr, ipv4_addr, mac)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""",(
				router_id,n["name"],n["mtu"],n["traffic"]["rx_bytes"],n["traffic"]["tx_bytes"],n["traffic"]["rx"],n["traffic"]["tx"],n["ipv6_fe80_addr"],n["ipv4_addr"],n["mac"],))
			for a in n["ipv6_addrs"]:
				cur.execute("INSERT INTO router_ipv6 (router, netif, ipv6) VALUES (%s, %s, %s)",(router_id,n["name"],a,))
		
		for n in router_update["neighbours"]:
			cur.execute("INSERT INTO router_neighbor (router, mac, quality, net_if, type) VALUES (%s, %s, %s, %s, %s)",(router_id,n["mac"],n["quality"],n["net_if"],n["type"],))
		
		status = router_update["status"]
	except ValueError as e:
		import traceback
		print("Warning: Unable to parse xml from %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router_id:
			set_status(mysql,router_id,"unknown")
		status = "unknown"
		status_comment = "Invalid XML"
	except OverflowError as e:
		import traceback
		print("Warning: Overflow Error when saving %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router_id:
			set_status(mysql,router_id,"unknown")
		status = "unknown"
		status_comment = "Integer Overflow"
	except Exception as e:
		import traceback
		print("Warning: Exception occurred when saving %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router_id:
			set_status(mysql,router_id,"unknown")
		status = "unknown"
		status_comment = "Exception occurred"

	if olddata:
		# fire events
		with suppress(KeyError, TypeError, UnboundLocalError):
			if olddata["uptime"] > router_update["system"]["uptime"]:
				events_append(mysql,router_id,"reboot","")

		with suppress(KeyError, TypeError, UnboundLocalError):
			if olddata["firmware"] != router_update["software"]["firmware"]:
				events_append(mysql,router_id,"update",
					"%s -> %s" % (olddata["firmware"], router_update["software"]["firmware"]))
				#events.append({
				#	"time": utcnow(),
				#	"type": "update",
				#	"comment": "%s -> %s" % (olddata["firmware"], router_update["software"]["firmware"]),
				#})

		with suppress(KeyError, TypeError, UnboundLocalError):
			if olddata["hostname"] != router_update["hostname"]:
				events_append(mysql,router_id,"hostname",
					"%s -> %s" % (olddata["hostname"], router_update["hostname"]))
				#events.append({
				#	"time": utcnow(),
				#	"type": "hostname",
				#	"comment": "%s -> %s" % (olddata["hostname"], router_update["hostname"]),
				#})

		with suppress(KeyError, TypeError, UnboundLocalError):
			if olddata["hood"] != router_update["hood"]:
				events_append(mysql,router_id,"hood",
					"%s -> %s" % (olddata["hood"], router_update["hood"]))
				#events.append({
				#	"time": utcnow(),
				#	"type": "hood",
				#	"comment": "%s -> %s" % (olddata["hood"], router_update["hood"]),
				#})

		with suppress(KeyError, TypeError):
			if olddata["status"] != status:
				events_append(mysql,router_id,status,status_comment)
				#event = {
				#	"time": utcnow(),
				#	"type": status,
				#}
				#with suppress(NameError):
				#	event["comment"] = status_comment
				#events.append(event)

def detect_offline_routers(mysql):
	cur = mysql.cursor()
	
	threshold=mysql.formatdt(utcnow() - datetime.timedelta(minutes=CONFIG["offline_threshold_minutes"]))
	now=mysql.utcnow()
	
	cur.execute("""
		SELECT id
		FROM router
		WHERE last_contact < %s AND status <> 'offline'
	""",(threshold,))
	result = cur.fetchall()
	for r in result:
		cur.execute("""
			INSERT INTO router_events ( router, time, type, comment )
			VALUES (%s, %s, 'offline', '')
		""",(r["id"],now,))
	
	cur.execute("""
		UPDATE router
		SET status = 'offline', clients = 0
		WHERE last_contact < %s AND status <> 'offline'
	""",(threshold,))
	mysql.commit()

def delete_orphaned_routers(mysql):
	cur = mysql.cursor()
	
	threshold=mysql.formatdt(utcnow() - datetime.timedelta(days=CONFIG["orphan_threshold_days"]))
	
	cur.execute("""
		DELETE r, e, i, nb, net FROM router AS r
		INNER JOIN router_events AS e ON r.id = e.router
		INNER JOIN router_ipv6 AS i ON r.id = i.router
		INNER JOIN router_neighbor AS nb ON r.id = nb.router
		INNER JOIN router_netif AS net ON r.id = net.router
		WHERE r.last_contact < %s AND r.status <> 'offline'
	""",(threshold,))
	
	mysql.commit()

def delete_old_stats(mysql):
	threshold=mysql.formatdt(utcnow() - datetime.timedelta(days=CONFIG["router_stat_days"]))
	
	mysql.execute("""
		DELETE FROM router_stats
		WHERE time < %s
	""",(threshold,))

	mysql.execute("""
		DELETE FROM router_stats_neighbor
		WHERE time < %s
	""",(threshold,))

	mysql.execute("""
		DELETE FROM router_stats_netif
		WHERE time < %s
	""",(threshold,))

	mysql.commit()

def events_append(mysql,router_id,event,comment):
	mysql.execute("""
		INSERT INTO router_events (router, time, type, comment)
		VALUES (%s, %s, %s, %s)
	""",(
		router_id,
		mysql.utcnow(),
		event,
		comment,))

def set_status(mysql,router_id,status):
	mysql.execute("""
		UPDATE router
		SET status = %s, last_contact = %s
		WHERE id = %s
	""",(
		status,
		mysql.utcnow(),
		router_id,))

def new_router_stats(mysql, router_id, uptime, router_update):
	if uptime < router_update["system"]["uptime"]:
		time = mysql.utcnow()
		
		mysql.execute("""
			INSERT INTO router_stats (router, time, sys_memfree, sys_membuff, sys_memcache, loadavg, sys_procrun, sys_proctot, clients)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
		""",(
			router_id,
			time,
			router_update["system"]["memory"]['free'],
			router_update["system"]["memory"]['buffering'],
			router_update["system"]["memory"]['caching'],
			router_update["system"]["loadavg"],
			router_update["system"]["processes"]['runnable'],
			router_update["system"]["processes"]['total'],
			router_update["system"]["clients"],))
		
		for netif in router_update["netifs"]:
			# sanitize name
			name = netif["name"].replace(".", "").replace("$", "")
			with suppress(KeyError):
				mysql.execute("""
					INSERT INTO router_stats_netif (router, netif, time, rx, tx)
					VALUES (%s, %s, %s, %s, %s)
				""",(
					router_id,
					name,
					time,
					netif["traffic"]["rx"],
					netif["traffic"]["tx"],))
		for neighbour in router_update["neighbours"]:
			with suppress(KeyError):
				mysql.execute("""
					INSERT INTO router_stats_neighbor (router, mac, time, quality)
					VALUES (%s, %s, %s, %s)
				""",(
					router_id,
					neighbour["mac"],
					time,
					neighbour["quality"],))

def calculate_network_io(cur, router_id, uptime, router_update):
	"""
	router: old router dict
	router_update: new router dict (which will be updated with new data)
	"""
	cur.execute("SELECT netif, rx_bytes, tx_bytes, rx, tx FROM router_netif WHERE router = %s",(router_id,));
	results = cur.fetchall()
	
	with suppress(KeyError, StopIteration):
		if uptime < router_update["system"]["uptime"]:
			timediff =  router_update["system"]["uptime"] - uptime
			for row in results:
				netif_update = next(filter(lambda n: n["name"] == row["netif"], router_update["netifs"]))
				rx_diff = netif_update["traffic"]["rx_bytes"] - int(row["rx_bytes"])
				tx_diff = netif_update["traffic"]["tx_bytes"] - int(row["tx_bytes"])
				if rx_diff >= 0 and tx_diff >= 0:
					netif_update["traffic"]["rx"] = int(rx_diff / timediff)
					netif_update["traffic"]["tx"] = int(tx_diff / timediff)
		else:
			for row in results:
				netif_update = next(filter(lambda n: n["name"] == row["netif"], router_update["netifs"]))
				netif_update["traffic"]["rx"] = int(row["rx"])
				netif_update["traffic"]["tx"] = int(row["tx"])
	
	return uptime

def parse_nodewatcher_xml(xml):
	try:
		assert xml != ""
		tree = lxml.etree.fromstring(xml)

		router_update = {
			"status": tree.xpath("/data/system_data/status/text()")[0],
			"hostname": tree.xpath("/data/system_data/hostname/text()")[0],
			"last_contact": utcnow().strftime('%Y-%m-%d %H:%M:%S'),
			"neighbours": [],
			"netifs": [],
			"system": {
				"time": datetime.datetime.fromtimestamp(int(tree.xpath("/data/system_data/local_time/text()")[0])).strftime('%Y-%m-%d %H:%M:%S'),
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

		# data.system_data.description
		with suppress(IndexError):
			router_update["description"] = ""
			router_update["description"] = tree.xpath("/data/system_data/description/text()")[0]

		# data.system_data.position_comment
		with suppress(IndexError):
			router_update["position_comment"] = ""
			router_update["position_comment"] = tree.xpath("/data/system_data/position_comment/text()")[0]

		# data.system_data.firmware_community
		with suppress(IndexError):
			router_update["community"] = ""
			router_update["community"] = tree.xpath("/data/system_data/firmware_community/text()")[0]

		# data.system_data.hood
		with suppress(IndexError):
			router_update["hood"] = ""
			router_update["hood"] = tree.xpath("/data/system_data/hood/text()")[0].lower()

		# data.system_data.status_text
		with suppress(IndexError):
			router_update["system"]["status_text"] = ""
			router_update["system"]["status_text"] = tree.xpath("/data/system_data/status_text/text()")[0]

		# data.system_data.contact
		with suppress(IndexError):
			router_update["system"]["contact"] = ""
			#router_update["user"] = ""
			router_update["system"]["contact"] = tree.xpath("/data/system_data/contact/text()")[0]
			#user = db.users.find_one({"email": router_update["system"]["contact"]})
			#if user:
			#	# post-netmon router gets its user assigned
			#	#router_update["user"] = {"nickname": user["nickname"], "_id": user["_id"]}
			#	router_update["user"] = user["nickname"]

		# data.system_data.geo
		with suppress(AssertionError, IndexError):
			lng = float(tree.xpath("/data/system_data/geo/lng/text()")[0])
			lat = float(tree.xpath("/data/system_data/geo/lat/text()")[0])
			assert lng != 0
			assert lat != 0

			router_update["lng"] = lng
			router_update["lat"] = lat

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
					"rx": 0,
					"tx": 0,
				},
			}
			with suppress(IndexError):
				interface["ipv6_fe80_addr"] = ""
				interface["ipv6_fe80_addr"] = netif.xpath("ipv6_link_local_addr/text()")[0].lower().split("/")[0]
			interface["ipv6_addrs"] = []
			if len(netif.xpath("ipv6_addr/text()")) > 0:
				for ipv6_addr in netif.xpath("ipv6_addr/text()"):
					interface["ipv6_addrs"].append(ipv6_addr.lower().split("/")[0])
			with suppress(IndexError):
				interface["ipv4_addr"] = ""
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
					"type": "l2"
				}
				router_update["neighbours"].append(neighbour)

		l3_neighbours = get_l3_neighbours(tree)
		visible_neighbours += len(l3_neighbours)
		router_update["system"]["visible_neighbours"] = visible_neighbours
		router_update["neighbours"] += l3_neighbours

		return router_update
	except (AssertionError, lxml.etree.XMLSyntaxError, IndexError) as e:
		raise ValueError("%s: %s" % (e.__class__.__name__, str(e)))

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
