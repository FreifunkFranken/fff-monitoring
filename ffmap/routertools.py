#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL
from ffmap.misc import *
from ffmap.config import CONFIG
import MySQLdb as my

import lxml.etree
import datetime
import requests
import time
from bson import SON
from contextlib import suppress

router_rate_limit_list = {}

def delete_router(mysql,dbid):
	mysql.execute("DELETE FROM router WHERE id = %s",(dbid,))
	mysql.execute("DELETE FROM router_netif WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_ipv6 WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_neighbor WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_events WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_stats WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_stats_neighbor WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_stats_netif WHERE router = %s",(dbid,))
	mysql.commit()

def ban_router(mysql,dbid):
	mac = mysql.findone("""
		SELECT mac
		FROM router_netif
		WHERE router = %s AND netif = 'br-mesh'
	""",(dbid,),"mac")
	added = mysql.utcnow()
	if mac:
		mysql.execute("INSERT INTO banned (mac, added) VALUES (%s, %s)",(mac,added,))
		mysql.commit()

def import_nodewatcher_xml(mysql, mac, xml, banned, netifdict):
	global router_rate_limit_list

	t = utcnow()
	if mac in router_rate_limit_list:
		if (t - router_rate_limit_list[mac]) < datetime.timedelta(minutes=5):
			return
	router_rate_limit_list[mac] = t

	# The following values should stay available after router reset
	keepvalues = ['lat','lng','description','position_comment','contact']

	router_id = None
	olddata = False
	uptime = 0
	events = []
	status_comment = ""
	reset = False
	
	try:
		findrouter = mysql.findone("SELECT router FROM router_netif WHERE mac = %s LIMIT 1",(mac.lower(),))
		router_update = parse_nodewatcher_xml(xml)
		
		# cancel if banned mac found
		for n in router_update["netifs"]:
			if n["mac"] in banned:
				return
		
		if router_update["status"] == "wrongpos":
			router_update["status"] = "unknown"
			status_comment = "Coordinates are wrong"
		status = router_update["status"]
		
		if findrouter:
			router_id = findrouter["router"]
			olddata = mysql.findone("SELECT sys_uptime, firmware, hostname, hood, status, lat, lng, contact, description, position_comment FROM router WHERE id = %s LIMIT 1",(router_id,))
			if olddata:
				uptime = olddata["sys_uptime"]

		# keep hood up to date
		if not router_update["hood"]:
			# router didn't send his hood in XML
			lat = router_update.get("lat")
			lng = router_update.get("lng")
			#if olddata and not lat and not lng:
			#	# hoods might change as well
			#	lat = olddata.get("lat")
			#	lng = olddata.get("lng")
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
		if not router_update["hood"]:
			router_update["hood"] = "Default"
		if not router_update['lat'] and not router_update['lng'] and olddata and olddata['lat'] and olddata['lng']:
			# Enable reset state; do before variable fallback
			reset = True
		
		if not router_update['hostname']:
			router_update['hostname'] = 'Give Me A Name'
		
		if olddata:
			# Has to be done after hood detection, so default hood is selected if no lat/lng
			for v in keepvalues:
				if not router_update[v]:
					router_update[v] = olddata[v] # preserve contact information after router reset
		
		if router_id:
			# statistics
			calculate_network_io(mysql, router_id, uptime, router_update)
			ru = router_update
			mysql.execute("""
				UPDATE router
				SET status = %s, hostname = %s, last_contact = %s, sys_time = %s, sys_uptime = %s, sys_memfree = %s, sys_membuff = %s, sys_memcache = %s,
				sys_loadavg = %s, sys_procrun = %s, sys_proctot = %s, clients = %s, wan_uplink = %s, cpu = %s, chipset = %s, hardware = %s, os = %s,
				batman = %s, kernel = %s, nodewatcher = %s, firmware = %s, firmware_rev = %s, description = %s, position_comment = %s, community = %s, hood = %s,
				status_text = %s, contact = %s, lng = %s, lat = %s, neighbors = %s, reset = %s
				WHERE id = %s
			""",(
				ru["status"],ru["hostname"],ru["last_contact"],ru["sys_time"],ru["sys_uptime"],ru["memory"]["free"],ru["memory"]["buffering"],ru["memory"]["caching"],
				ru["sys_loadavg"],ru["processes"]["runnable"],ru["processes"]["total"],ru["clients"],ru["has_wan_uplink"],ru["cpu"],ru["chipset"],ru["hardware"],ru["os"],
				ru["batman_adv"],ru["kernel"],ru["nodewatcher"],ru["firmware"],ru["firmware_rev"],ru["description"],ru["position_comment"],ru["community"],ru["hood"],
				ru["status_text"],ru["contact"],ru["lng"],ru["lat"],ru["visible_neighbours"],reset,router_id,))
			
			# Previously, I just deleted all entries and recreated them again with INSERT.
			# Although this is simple to write and actually includes less queries, it causes a lot more write IO.
			# Since most of the neighbors and interfaces do NOT change frequently, it is worth the extra effort to delete only those really gone since the last update.
			nkeys = []
			akeys = []
			for n in router_update["netifs"]:
				nkeys.append(n["name"])
				if n["name"]=='br-mesh': # Only br-mesh will normally have assigned IPv6 addresses
					akeys = n["ipv6_addrs"]
			
			if nkeys:
				mysql.execute("DELETE FROM router_netif WHERE router = %s AND netif NOT IN ({})".format(','.join(['%s'] * len(nkeys))),tuple([router_id] + nkeys))
			else:
				mysql.execute("DELETE FROM router_netif WHERE router = %s",(router_id,))
			if akeys:
				mysql.execute("DELETE FROM router_ipv6 WHERE router = %s AND netif = 'br-mesh' AND ipv6 NOT IN ({})".format(','.join(['%s'] * len(akeys))),tuple([router_id] + akeys))
				mysql.execute("DELETE FROM router_ipv6 WHERE router = %s AND netif <> 'br-mesh'",(router_id,))
			else:
				mysql.execute("DELETE FROM router_ipv6 WHERE router = %s",(router_id,))
			
			nbkeys = []
			for n in router_update["neighbours"]:
				nbkeys.append(n["mac"])
			if nbkeys:
				mysql.execute("DELETE FROM router_neighbor WHERE router = %s AND mac NOT IN ({})".format(','.join(['%s'] * len(nbkeys))),tuple([router_id] + nbkeys))
			else:
				mysql.execute("DELETE FROM router_neighbor WHERE router = %s",(router_id,))
			
			gwkeys = []
			for g in router_update["gws"]:
				gwkeys.append(g["mac"])
			if gwkeys:
				mysql.execute("DELETE FROM router_gw WHERE router = %s AND mac NOT IN ({})".format(','.join(['%s'] * len(gwkeys))),tuple([router_id] + gwkeys))
			else:
				mysql.execute("DELETE FROM router_gw WHERE router = %s",(router_id,))
			
		else:
			# insert new router
			created = mysql.utcnow()
			#events = [] # don't fire sub-events of created events
			ru = router_update
			router_update["status"] = "online" # use 'online' here, as anything different is only evaluated if olddata is present
			mysql.execute("""
				INSERT INTO router (status, hostname, created, last_contact, sys_time, sys_uptime, sys_memfree, sys_membuff, sys_memcache,
				sys_loadavg, sys_procrun, sys_proctot, clients, wan_uplink, cpu, chipset, hardware, os,
				batman, kernel, nodewatcher, firmware, firmware_rev, description, position_comment, community, hood,
				status_text, contact, lng, lat, neighbors)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""",(
				ru["status"],ru["hostname"],created,ru["last_contact"],ru["sys_time"],ru["sys_uptime"],ru["memory"]["free"],ru["memory"]["buffering"],ru["memory"]["caching"],
				ru["sys_loadavg"],ru["processes"]["runnable"],ru["processes"]["total"],ru["clients"],ru["has_wan_uplink"],ru["cpu"],ru["chipset"],ru["hardware"],ru["os"],
				ru["batman_adv"],ru["kernel"],ru["nodewatcher"],ru["firmware"],ru["firmware_rev"],ru["description"],ru["position_comment"],ru["community"],ru["hood"],
				ru["status_text"],ru["contact"],ru["lng"],ru["lat"],ru["visible_neighbours"],))
			router_id = mysql.cursor().lastrowid
			
			events_append(mysql,router_id,"created","")
		
		ndata = []
		adata = []
		for n in router_update["netifs"]:
			ndata.append((router_id,n["name"],n["mtu"],n["traffic"]["rx_bytes"],n["traffic"]["tx_bytes"],n["traffic"]["rx"],n["traffic"]["tx"],n["ipv6_fe80_addr"],n["ipv4_addr"],n["mac"],n["wlan_channel"],n["wlan_type"],n["wlan_width"],n["wlan_ssid"],n["wlan_txpower"],))
			for a in n["ipv6_addrs"]:
				adata.append((router_id,n["name"],a,))
		
		# As for deletion, it is more complex to do work with ON DUPLICATE KEY UPDATE instead of plain DELETE and INSERT,
		# but with this we have much less IO and UPDATE is better than INSERT in terms of locking
		mysql.executemany("""
			INSERT INTO router_netif (router, netif, mtu, rx_bytes, tx_bytes, rx, tx, fe80_addr, ipv4_addr, mac, wlan_channel, wlan_type, wlan_width, wlan_ssid, wlan_txpower)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				mtu=VALUES(mtu),
				rx_bytes=VALUES(rx_bytes),
				tx_bytes=VALUES(tx_bytes),
				rx=VALUES(rx),
				tx=VALUES(tx),
				fe80_addr=VALUES(fe80_addr),
				ipv4_addr=VALUES(ipv4_addr),
				mac=VALUES(mac),
				wlan_channel=VALUES(wlan_channel),
				wlan_type=VALUES(wlan_type),
				wlan_width=VALUES(wlan_width),
				wlan_ssid=VALUES(wlan_ssid),
				wlan_txpower=VALUES(wlan_txpower)
		""",ndata)
		mysql.executemany("""
			INSERT INTO router_ipv6 (router, netif, ipv6)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE
				ipv6=ipv6
		""",adata)
		
		nbdata = []
		for n in router_update["neighbours"]:
			nbdata.append((router_id,n["mac"],n["netif"],n["quality"],n["type"],))
		
		mysql.executemany("""
			INSERT INTO router_neighbor (router, mac, netif, quality, type)
			VALUES (%s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				netif=VALUES(netif),
				quality=VALUES(quality),
				type=VALUES(type)
		""",nbdata)
		
		gwdata = []
		for g in router_update["gws"]:
			gwdata.append((router_id,g["mac"],g["batX"],g["quality"],g["nexthop"],g["netif"],g["gw_class"],g["selected"],))
		
		mysql.executemany("""
			INSERT INTO router_gw (router, mac, batX, quality, nexthop, netif, gw_class, selected)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				batX=VALUES(batX),
				quality=VALUES(quality),
				nexthop=VALUES(nexthop),
				netif=VALUES(netif),
				gw_class=VALUES(gw_class),
				selected=VALUES(selected)
		""",gwdata)
		
		if router_id:
			new_router_stats(mysql, router_id, uptime, router_update, netifdict)
		
	except ValueError as e:
		import traceback
		writefulllog("Warning: Unable to parse xml from %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router_id:
			set_status(mysql,router_id,"unknown")
		status = "unknown"
		status_comment = "Invalid XML"
	except OverflowError as e:
		import traceback
		writefulllog("Warning: Overflow Error when saving %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router_id:
			set_status(mysql,router_id,"unknown")
		status = "unknown"
		status_comment = "Integer Overflow"
	except my.OperationalError as e:
		import traceback
		writefulllog("Warning: Operational error in MySQL when saving %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		writelog(CONFIG["debug_dir"] + "/fail_readrouter.txt", "MySQL Error: {} - {}".format(router_update["hostname"],e))
	except Exception as e:
		import traceback
		writefulllog("Warning: Exception occurred when saving %s: %s\n__%s" % (mac, e, traceback.format_exc().replace("\n", "\n__")))
		if router_id:
			set_status(mysql,router_id,"unknown")
		status = "unknown"
		status_comment = "Exception occurred"
		writelog(CONFIG["debug_dir"] + "/fail_readrouter.txt", "General Exception: {} - {}".format(router_update["hostname"],e))

	if olddata:
		# fire events
		with suppress(KeyError, TypeError, UnboundLocalError):
			if (olddata["sys_uptime"] - 300) > router_update["sys_uptime"]:
				events_append(mysql,router_id,"reboot","")

		with suppress(KeyError, TypeError, UnboundLocalError):
			if olddata["firmware"] != router_update["firmware"]:
				events_append(mysql,router_id,"update",
					"%s -> %s" % (olddata["firmware"], router_update["firmware"]))

		with suppress(KeyError, TypeError, UnboundLocalError):
			if olddata["hostname"] != router_update["hostname"]:
				events_append(mysql,router_id,"hostname",
					"%s -> %s" % (olddata["hostname"], router_update["hostname"]))

		with suppress(KeyError, TypeError, UnboundLocalError):
			if olddata["hood"] != router_update["hood"]:
				events_append(mysql,router_id,"hood",
					"%s -> %s" % (olddata["hood"], router_update["hood"]))

		with suppress(KeyError, TypeError):
			if olddata["status"] != status:
				events_append(mysql,router_id,status,status_comment)

def detect_offline_routers(mysql):
	# Offline after X minutes (online -> offline)
	
	threshold=mysql.formatdt(utcnow() - datetime.timedelta(minutes=CONFIG["offline_threshold_minutes"]))
	now=mysql.utcnow()
	
	result = mysql.fetchall("""
		SELECT id
		FROM router
		WHERE last_contact < %s AND status <> 'offline' AND status <> 'orphaned'
	""",(threshold,))
	
	rdata = []
	for r in result:
		rdata.append((r["id"],now,))
	mysql.executemany("""
		INSERT INTO router_events ( router, time, type, comment )
		VALUES (%s, %s, 'offline', '')
	""",rdata)
	
	mysql.execute("""
		UPDATE router
		SET status = 'offline', clients = 0
		WHERE last_contact < %s AND status <> 'offline' AND status <> 'orphaned'
	""",(threshold,))
	mysql.commit()

def detect_orphaned_routers(mysql):
	# Orphan after X days (offline -> orphaned)
	
	threshold=mysql.formatdt(utcnow() - datetime.timedelta(days=CONFIG["orphan_threshold_days"]))
	
	mysql.execute("""
		UPDATE router
		SET status = 'orphaned'
		WHERE last_contact < %s AND status = 'offline'
	""",(threshold,))
	mysql.commit()

def delete_orphaned_routers(mysql):
	# Deleted after X days (orphaned -> deletion)
	
	threshold=mysql.formatdt(utcnow() - datetime.timedelta(days=CONFIG["delete_threshold_days"]))
	
	mysql.execute("""
		DELETE r, e, i, nb, net FROM router AS r
		INNER JOIN router_events AS e ON r.id = e.router
		INNER JOIN router_ipv6 AS i ON r.id = i.router
		INNER JOIN router_neighbor AS nb ON r.id = nb.router
		INNER JOIN router_netif AS net ON r.id = net.router
		WHERE r.last_contact < %s AND r.status <> 'offline'
	""",(threshold,))
	mysql.commit()

def delete_old_stats(mysql):
	threshold=(utcnow() - datetime.timedelta(days=CONFIG["router_stat_days"])).timestamp()
	
	start_time = time.time()
	mysql.execute("""
		DELETE s FROM router_stats AS s
		LEFT JOIN router AS r ON s.router = r.id
		WHERE s.time < %s AND (r.status = 'online' OR r.status IS NULL)
	""",(threshold,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Delete stats: %.3f seconds" % (time.time() - start_time))
	print("--- Delete stats: %.3f seconds ---" % (time.time() - start_time))

	time.sleep(10)
	start_time = time.time()
	mysql.execute("""
		DELETE s FROM router_stats_gw AS s
		LEFT JOIN router AS r ON s.router = r.id
		WHERE s.time < %s AND (r.status = 'online' OR r.status IS NULL)
	""",(threshold,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Delete gw-stats: %.3f seconds" % (time.time() - start_time))
	print("--- Delete gw-stats: %.3f seconds ---" % (time.time() - start_time))

	time.sleep(10)
	start_time = time.time()
	mysql.execute("""
		DELETE s FROM router_stats_neighbor AS s
		LEFT JOIN router AS r ON s.router = r.id
		WHERE s.time < %s AND (r.status = 'online' OR r.status IS NULL)
	""",(threshold,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Delete neighbor-stats: %.3f seconds" % (time.time() - start_time))
	print("--- Delete neighbor-stats: %.3f seconds ---" % (time.time() - start_time))

	time.sleep(10)
	start_time = time.time()
	mysql.execute("""
		UPDATE router_stats_netif AS s
		LEFT JOIN router AS r ON s.router = r.id
		SET s.deletebit = 1
		WHERE s.time < %s AND (r.status = 'online' OR r.status IS NULL)
	""",(threshold,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Update netif stats: %.3f seconds" % (time.time() - start_time))
	print("--- Update netif stats: %.3f seconds ---" % (time.time() - start_time))
	
	time.sleep(30)
	minustime=0
	rowsaffected=1
	start_time = time.time()
	while rowsaffected > 0:
		try:
			rowsaffected = mysql.execute("""
				DELETE FROM router_stats_netif
				WHERE deletebit = 1
				LIMIT 50000
			""")
			mysql.commit()
		except my.OperationalError:
			rowsaffected = 1
		time.sleep(10)
		minustime += 10
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Delete netif stats: %.3f seconds" % (time.time() - start_time - minustime))
	print("--- Delete netif stats: %.3f seconds ---" % (time.time() - start_time - minustime))

	start_time = time.time()
	events = mysql.fetchall("""
		SELECT router, COUNT(time) AS count FROM router_events
		GROUP BY router
	""")
	
	for e in events:
		delnum = int(e["count"] - CONFIG["event_num_entries"])
		if delnum > 0:
			mysql.execute("""
				DELETE FROM router_events
				WHERE router = %s
				ORDER BY time ASC
				LIMIT %s
			""",(e["router"],delnum,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Delete events: %.3f seconds" % (time.time() - start_time))
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "-------")
	print("--- Delete events: %.3f seconds ---" % (time.time() - start_time))

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

def new_router_stats(mysql, router_id, uptime, router_update, netifdict):
	if (uptime + CONFIG["router_stat_mindiff_secs"]) < router_update["sys_uptime"]:
		time = mysql.utctimestamp()
		
		stattime = mysql.findone("SELECT time FROM router_stats WHERE router = %s ORDER BY time DESC LIMIT 1",(router_id,),"time")
		if not stattime or (stattime + CONFIG["router_stat_mindiff_default"]) < time:
			mysql.execute("""
				INSERT INTO router_stats (time, router, sys_memfree, sys_membuff, sys_memcache, loadavg, sys_procrun, sys_proctot, clients)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
			""",(
				time,
				router_id,
				router_update["memory"]['free'],
				router_update["memory"]['buffering'],
				router_update["memory"]['caching'],
				router_update["sys_loadavg"],
				router_update["processes"]['runnable'],
				router_update["processes"]['total'],
				router_update["clients"],))
		
		netiftime = mysql.findone("SELECT time FROM router_stats_netif WHERE router = %s ORDER BY time DESC LIMIT 1",(router_id,),"time")
		if not netiftime or (netiftime + CONFIG["router_stat_mindiff_netif"]) < time:
			ndata = []
			nkeys = []
			for netif in router_update["netifs"]:
				# sanitize name
				name = netif["name"].replace(".", "").replace("$", "")
				with suppress(KeyError):
					if name in netifdict.keys():
						ndata.append((time,router_id,netifdict[name],netif["traffic"]["rx"],netif["traffic"]["tx"],))
					else:
						nkeys.append((name,))
			
			# 99.9 % of the routers will NOT enter this, so the doubled code is not a problem
			if nkeys:
				mysql.executemany("""
					INSERT INTO netifs (name)
					VALUES (%s)
					ON DUPLICATE KEY UPDATE name=name
				""",nkeys)
				netifdict = mysql.fetchdict("SELECT id, name FROM netifs",(),"name","id")
				
				ndata = []
				for netif in router_update["netifs"]:
					# sanitize name
					name = netif["name"].replace(".", "").replace("$", "")
					with suppress(KeyError):
						ndata.append((time,router_id,netifdict[name],netif["traffic"]["rx"],netif["traffic"]["tx"],))
			
			mysql.executemany("""
				INSERT INTO router_stats_netif (time, router, netif, rx, tx)
				VALUES (%s, %s, %s, %s, %s)
			""",ndata)
		
		# reuse timestamp from router_stats to avoid additional queries
		if not stattime or (stattime + CONFIG["router_stat_mindiff_default"]) < time:
			nbdata = []
			for neighbour in router_update["neighbours"]:
				with suppress(KeyError):
					nbdata.append((time,router_id,neighbour["mac"],neighbour["quality"],))
			mysql.executemany("""
				INSERT INTO router_stats_neighbor (time, router, mac, quality)
				VALUES (%s, %s, %s, %s)
			""",nbdata)
		
		# reuse timestamp from router_stats to avoid additional queries
		if not stattime or (stattime + CONFIG["router_stat_mindiff_default"]) < time:
			gwdata = []
			for gw in router_update["gws"]:
				with suppress(KeyError):
					gwdata.append((time,router_id,gw["mac"],gw["quality"],))
			mysql.executemany("""
				INSERT INTO router_stats_gw (time, router, mac, quality)
				VALUES (%s, %s, %s, %s)
			""",gwdata)

def calculate_network_io(mysql, router_id, uptime, router_update):
	"""
	router: old router dict
	router_update: new router dict (which will be updated with new data)
	"""
	results = mysql.fetchall("SELECT netif, rx_bytes, tx_bytes FROM router_netif WHERE router = %s",(router_id,));
	
	with suppress(KeyError, StopIteration):
		if uptime < router_update["sys_uptime"]:
			timediff =  router_update["sys_uptime"] - uptime
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
				netif_update["traffic"]["rx"] = int(netif_update["traffic"]["rx_bytes"] / router_update["sys_uptime"])
				netif_update["traffic"]["tx"] = int(netif_update["traffic"]["tx_bytes"] / router_update["sys_uptime"])
	
	return uptime

def evalxpath(tree,p,default=""):
	tmp = default
	with suppress(IndexError):
		tmp = tree.xpath(p)[0]
	return tmp

def evalxpathfloat(tree,p,default=0):
	tmp = default
	with suppress(IndexError):
		tmp = float(tree.xpath(p)[0])
	return tmp

def evalxpathint(tree,p,default=0):
	tmp = default
	with suppress(IndexError):
		tmp = int(tree.xpath(p)[0])
	return tmp

def evalxpathbool(tree,p):
	tmp = False
	with suppress(IndexError):
		tmp = tree.xpath(p)[0]
	if tmp:
		return (tmp.lower()=="true" or tmp=="1")
	return False

def parse_nodewatcher_xml(xml):
	try:
		assert xml != ""
		tree = lxml.etree.fromstring(xml)

		router_update = {
			"status": evalxpath(tree,"/data/system_data/status/text()"),
			"hostname": evalxpath(tree,"/data/system_data/hostname/text()"),
			"last_contact": utcnow().strftime('%Y-%m-%d %H:%M:%S'),
			"gws": [],
			"neighbours": [],
			"netifs": [],
			# hardware
			"chipset": evalxpath(tree,"/data/system_data/chipset/text()","Unknown"),
			"cpu": evalxpath(tree,"/data/system_data/cpu/text()"),
			"hardware": evalxpath(tree,"/data/system_data/model/text()","Legacy"),
			# config
			"description": evalxpath(tree,"/data/system_data/description/text()"),
			"position_comment": evalxpath(tree,"/data/system_data/position_comment/text()"),
			"community": evalxpath(tree,"/data/system_data/firmware_community/text()"),
			"hood": evalxpath(tree,"/data/system_data/hood/text()"),
			"status_text": evalxpath(tree,"/data/system_data/status_text/text()"),
			"contact": evalxpath(tree,"/data/system_data/contact/text()"),
			# system
			"sys_time": datetime.datetime.fromtimestamp(evalxpathint(tree,"/data/system_data/local_time/text()")).strftime('%Y-%m-%d %H:%M:%S'),
			"sys_uptime": int(evalxpathfloat(tree,"/data/system_data/uptime/text()")),
			"sys_loadavg": evalxpathfloat(tree,"/data/system_data/loadavg/text()"),
			"memory": {
				"free": evalxpathint(tree,"/data/system_data/memory_free/text()"),
				"buffering": evalxpathint(tree,"/data/system_data/memory_buffering/text()"),
				"caching": evalxpathint(tree,"/data/system_data/memory_caching/text()"),
			},
			"processes": {
				"runnable": int(evalxpath(tree,"/data/system_data/processes/text()").split("/")[0]),
				"total": int(evalxpath(tree,"/data/system_data/processes/text()").split("/")[1]),
			},
			"clients": evalxpathint(tree,"/data/client_count/text()"),
			"has_wan_uplink": (
				(len(tree.xpath("/data/system_data/vpn_active")) > 0
				and evalxpathint(tree,"/data/system_data/vpn_active/text()") == 1)
				or len(tree.xpath("/data/interface_data/%s" % CONFIG["vpn_netif"])) > 0
				or len(tree.xpath("/data/interface_data/*[starts-with(name(), '%s')]" % CONFIG["vpn_netif_l2tp"])) > 0
				or len(tree.xpath("/data/interface_data/%s" % CONFIG["vpn_netif_aux"])) > 0),
			# software
			"os": "%s (%s)" % (evalxpath(tree,"/data/system_data/distname/text()"),
					   evalxpath(tree,"/data/system_data/distversion/text()")),
			"batman_adv": evalxpath(tree,"/data/system_data/batman_advanced_version/text()"),
			"kernel": evalxpath(tree,"/data/system_data/kernel_version/text()"),
			"nodewatcher": evalxpath(tree,"/data/system_data/nodewatcher_version/text()"),
			#"fastd": evalxpath(tree,"/data/system_data/fastd_version/text()"),
			"firmware": evalxpath(tree,"/data/system_data/firmware_version/text()"),
			"firmware_rev": evalxpath(tree,"/data/system_data/firmware_revision/text()"),
		}

		try:
			lng = evalxpathfloat(tree,"/data/system_data/geo/lng/text()")
		except ValueError:
			lng = None
			router_update["status"] = "wrongpos"
		try:
			lat = evalxpathfloat(tree,"/data/system_data/geo/lat/text()")
		except ValueError:
			lat = None
			router_update["status"] = "wrongpos"
		
		if lng == 0:
			lng = None
		if lat == 0:
			lat = None
		router_update["lng"] = lng
		router_update["lat"] = lat

		#FIXME: tmp workaround to get similar hardware names
		router_update["hardware"] = router_update["hardware"].replace("nanostation-m", "Ubiquiti Nanostation M")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr1043nd-v1", "TP-Link TL-WR1043N/ND v1")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr1043nd-v2", "TP-Link TL-WR1043N/ND v2")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr741nd-v2", "TP-Link TL-WR741N/ND v2")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr741nd-v4", "TP-Link TL-WR741N/ND v4")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr841nd-v7", "TP-Link TL-WR841N/ND v7")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr841n-v8", "TP-Link TL-WR841N/ND v8")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr841n-v9", "TP-Link TL-WR841N/ND v9")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr841nd-v9", "TP-Link TL-WR841N/ND v9")
		router_update["hardware"] = router_update["hardware"].replace("tl-wr842n-v2", "TP-Link TL-WR842N/ND v2")
		router_update["hardware"] = router_update["hardware"].replace("tl-wdr4300", "TP-Link TL-WDR4300")

		for netif in tree.xpath("/data/interface_data/*"):
			interface = {
				"name": evalxpath(netif,"name/text()"),
				"mtu": evalxpathint(netif,"mtu/text()"),
				"traffic": {
					"rx_bytes": evalxpathint(netif,"traffic_rx/text()"),
					"tx_bytes": evalxpathint(netif,"traffic_tx/text()"),
					"rx": 0,
					"tx": 0,
				},
				"ipv4_addr": evalxpath(netif,"ipv4_addr/text()"),
				"mac": evalxpath(netif,"mac_addr/text()").lower(),
				"wlan_channel": evalxpathint(netif,"wlan_channel/text()",None),
				"wlan_type": evalxpath(netif,"wlan_type/text()",None),
				"wlan_width": evalxpathint(netif,"wlan_width/text()",None),
				"wlan_ssid": evalxpath(netif,"wlan_ssid/text()",None),
				"wlan_txpower": evalxpath(netif,"wlan_tx_power/text()",None),
			}
			with suppress(IndexError):
				interface["ipv6_fe80_addr"] = ""
				interface["ipv6_fe80_addr"] = netif.xpath("ipv6_link_local_addr/text()")[0].lower().split("/")[0]
			interface["ipv6_addrs"] = []
			if len(netif.xpath("ipv6_addr/text()")) > 0:
				for ipv6_addr in netif.xpath("ipv6_addr/text()"):
					interface["ipv6_addrs"].append(ipv6_addr.lower().split("/")[0])

			router_update["netifs"].append(interface)

		visible_neighbours = 0

		for originator in tree.xpath("/data/batman_adv_originators/*"):
			visible_neighbours += 1
			o_mac = evalxpath(originator,"originator/text()")
			o_nexthop = evalxpath(originator,"nexthop/text()")
			# mac is the mac of the neighbour w2/5mesh if
			# (which might also be called wlan0-1)
			o_link_quality = evalxpath(originator,"link_quality/text()")
			o_out_if = evalxpath(originator,"outgoing_interface/text()")
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
					"netif": o_out_if,
					"quality": int(o_link_quality),
					"type": "l2"
				}
				router_update["neighbours"].append(neighbour)

		l3_neighbours = get_l3_neighbours(tree)
		visible_neighbours += len(l3_neighbours)
		router_update["visible_neighbours"] = visible_neighbours
		router_update["neighbours"] += l3_neighbours
		
		for gw in tree.xpath("/data/batman_adv_gateway_list/*"):
			gw_mac = evalxpath(gw,"gateway/text()")
			if (gw_mac and len(gw_mac)>12): # Throw away headline
				gw = {
					"mac": gw_mac.lower(),
					"batX": None,
					"quality": evalxpathint(gw,"link_quality/text()"),
					"nexthop": evalxpath(gw,"nexthop/text()",None),
					"netif": evalxpath(gw,"outgoing_interface/text()",None),
					"gw_class": evalxpath(gw,"gw_class/text()",None),
					"selected": evalxpathbool(gw,"selected/text()")
				}
				if gw["netif"]=="false":
					tmp = gw["gw_class"].split(None,1)
					gw["netif"] = tmp[0]
					gw["gw_class"] = tmp[1]
				router_update["gws"].append(gw)

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
			"netif": out_if,
			"quality": -1,
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
