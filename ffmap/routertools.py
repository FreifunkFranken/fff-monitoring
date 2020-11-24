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
import ipaddress
from bson import SON
from contextlib import suppress

#router_rate_limit_list = {}

def delete_router(mysql,dbid):
	mysql.execute("DELETE FROM router WHERE id = %s",(dbid,))
	mysql.execute("DELETE FROM router_netif WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_ipv6 WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_neighbor WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_gw WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_events WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_stats WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_stats_neighbor WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_stats_netif WHERE router = %s",(dbid,))
	mysql.execute("DELETE FROM router_stats_gw WHERE router = %s",(dbid,))
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

def import_nodewatcher_xml(mysql, mac, xml, banned, hoodsv2, netifdict, hoodsdict, statstime):
	#global router_rate_limit_list

	#if mac in router_rate_limit_list:
	#	if (statstime - router_rate_limit_list[mac]) < datetime.timedelta(minutes=5):
	#		return
	#router_rate_limit_list[mac] = statstime

	# The following values should stay available after router reset
	keepvalues = ['lat','lng','description','position_comment','contact']

	router_id = None
	olddata = False
	uptime = 0
	events = []
	status_comment = ""
	reset = False
	
	try:
		findrouter = mysql.findone("SELECT router FROM router_netif WHERE mac = %s LIMIT 1",(mac2int(mac),))
		router_update = parse_nodewatcher_xml(xml,statstime)
		router_update["local"] = bool(router_update["v2"] and router_update["hood"] and not router_update["hood"] in hoodsv2)
		
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
			olddata = mysql.findone("""
				SELECT sys_uptime, sys_time, firmware, hostname, hoods.id AS hoodid, hoods.name AS hood, status, lat, lng, contact, description, position_comment, w2_active, w2_busy, w5_active, w5_busy
				FROM router
				LEFT JOIN hoods ON router.hood = hoods.id
				WHERE router.id = %s
				LIMIT 1
			""",(router_id,))
			if olddata:
				uptime = olddata["sys_uptime"]

				# Filter old data (Alfred keeps data for 10 min.; old and new can mix if gateways do not sync)
				# We only use data where system time is bigger than before (last entry) or more than 1 hour smaller (to catch cases without timeserver)
				newtime = router_update["sys_time"].timestamp()
				oldtime = olddata["sys_time"].timestamp()
				if not (newtime > oldtime or newtime < (oldtime - 3600)):
					return

				# Keep hood if not set (V2 only, "" != None)
				if router_update["hood"] == "":
					router_update["hood"] = olddata["hood"]
			else:
				delete_router(mysql,router_id)

		# keep hood up to date (extremely rare case where no olddata but no hood)
		if router_update["hood"] == "":
			router_update["hood"] = "NoHood"
		if not router_update["hood"]:
			# V1 Router
			router_update["hood"] = "Legacy"

		if not router_update['lat'] and not router_update['lng'] and olddata and olddata['lat'] and olddata['lng']:
			# Enable reset state; do before variable fallback
			reset = True

		if not router_update["hood"] in hoodsdict.keys():
			checkagain = mysql.findone("SELECT id FROM hoods WHERE name = %s",(router_update["hood"],),"id")
			# Prevent adding the same hood for all routers (won't break, but each will raise the AUTO_INCREMENT)
			if not checkagain:
				mysql.execute("""
					INSERT INTO hoods (name)
					VALUES (%s)
					ON DUPLICATE KEY UPDATE name=name
				""",(router_update["hood"],))
			hoodsdict = mysql.fetchdict("SELECT id, name FROM hoods",(),"name","id")
		router_update["hoodid"] = hoodsdict[router_update["hood"]]

		if not router_update['hostname']:
			router_update['hostname'] = 'Give Me A Name'
		
		if olddata:
			# Has to be done after hood detection, so default hood is selected if no lat/lng
			for v in keepvalues:
				if not router_update[v]:
					router_update[v] = olddata[v] # preserve contact information after router reset
		
		# Calculate airtime
		router_update["w2_airtime"] = None
		router_update["w5_airtime"] = None
		# Only use new data
		if olddata and router_update["sys_uptime"] > olddata["sys_uptime"]:
			fields_w2 = (router_update["w2_active"], router_update["w2_busy"], olddata["w2_busy"], olddata["w2_active"],)
			if not any(w == None for w in fields_w2):
				diff_active = router_update["w2_active"] - olddata["w2_active"]
				diff_busy = router_update["w2_busy"] - olddata["w2_busy"]
				if diff_active:
					router_update["w2_airtime"] = diff_busy / diff_active # auto float-division in Python3
				else:
					router_update["w2_airtime"] = 0
			fields_w5 = (router_update["w5_active"], router_update["w5_busy"], olddata["w5_busy"], olddata["w5_active"],)
			if not any(w == None for w in fields_w5):
				diff_active = router_update["w5_active"] - olddata["w5_active"]
				diff_busy = router_update["w5_busy"] - olddata["w5_busy"]
				if diff_active:
					router_update["w5_airtime"] = diff_busy / diff_active # auto float-division in Python3
				else:
					router_update["w5_airtime"] = 0
		
		if olddata:
			# statistics
			calculate_network_io(mysql, router_id, uptime, router_update)
			ru = router_update
			mysql.execute("""
				UPDATE router
				SET status = %s, hostname = %s, last_contact = %s, sys_time = %s, sys_uptime = %s, sys_memfree = %s, sys_membuff = %s, sys_memcache = %s,
				sys_loadavg = %s, sys_procrun = %s, sys_proctot = %s, clients = %s, clients_eth = %s, clients_w2 = %s, clients_w5 = %s,
				w2_active = %s, w2_busy = %s, w5_active = %s, w5_busy = %s, w2_airtime = %s, w5_airtime = %s, wan_uplink = %s, tc_enabled = %s, tc_in = %s, tc_out = %s,
				cpu = %s, chipset = %s, hardware = %s, os = %s, babel_version = %s,
				batman = %s, routing_protocol = %s, kernel = %s, nodewatcher = %s, firmware = %s, firmware_rev = %s, description = %s, position_comment = %s, community = %s, hood = %s, v2 = %s, local = %s, gateway = %s,
				status_text = %s, contact = %s, lng = %s, lat = %s, neighbors = %s, reset = %s
				WHERE id = %s
			""",(
				ru["status"],ru["hostname"],ru["last_contact"],ru["sys_time"].strftime('%Y-%m-%d %H:%M:%S'),ru["sys_uptime"],ru["memory"]["free"],ru["memory"]["buffering"],ru["memory"]["caching"],
				ru["sys_loadavg"],ru["processes"]["runnable"],ru["processes"]["total"],ru["clients"],ru["clients_eth"],ru["clients_w2"],ru["clients_w5"],
				ru["w2_active"],ru["w2_busy"],ru["w5_active"],ru["w5_busy"],ru["w2_airtime"],ru["w5_airtime"],ru["has_wan_uplink"],ru["tc_enabled"],ru["tc_in"],ru["tc_out"],
				ru["cpu"],ru["chipset"],ru["hardware"],ru["os"],ru["babel_version"],
				ru["batman_adv"],ru["rt_protocol"],ru["kernel"],ru["nodewatcher"],ru["firmware"],ru["firmware_rev"],ru["description"],ru["position_comment"],ru["community"],ru["hoodid"],ru["v2"],ru["local"],ru["gateway"],
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
				ndata = mysql.fetchall("SELECT netif FROM router_netif WHERE router = %s",(router_id,),"netif")
				for n in ndata:
					if n in nkeys:
						continue
					mysql.execute("DELETE FROM router_netif WHERE router = %s AND netif = %s",(router_id,n,))
			else:
				mysql.execute("DELETE FROM router_netif WHERE router = %s",(router_id,))
			if akeys:
				adata = mysql.fetchall("SELECT netif, ipv6 FROM router_ipv6 WHERE router = %s",(router_id,))
				for a in adata:
					if a["netif"]=='br-mesh' and a["ipv6"] in akeys:
						continue
					mysql.execute("DELETE FROM router_ipv6 WHERE router = %s AND netif = %s AND ipv6 = %s",(router_id,a["netif"],a["ipv6"],))
			else:
				mysql.execute("DELETE FROM router_ipv6 WHERE router = %s",(router_id,))
			
			nbkeys = []
			for n in router_update["neighbours"]:
				nbkeys.append(n["mac"])
			if nbkeys:
				nbdata = mysql.fetchall("SELECT mac FROM router_neighbor WHERE router = %s",(router_id,),"mac")
				for n in nbdata:
					if n in nbkeys:
						continue
					mysql.execute("DELETE FROM router_neighbor WHERE router = %s AND mac = %s",(router_id,n,))
			else:
				mysql.execute("DELETE FROM router_neighbor WHERE router = %s",(router_id,))
			
			gwkeys = []
			for g in router_update["gws"]:
				gwkeys.append(g["mac"])
			if gwkeys:
				gwdata = mysql.fetchall("SELECT mac FROM router_gw WHERE router = %s",(router_id,),"mac")
				for g in gwdata:
					if g in gwkeys:
						continue
					mysql.execute("DELETE FROM router_gw WHERE router = %s AND mac = %s",(router_id,g,))
			else:
				mysql.execute("DELETE FROM router_gw WHERE router = %s",(router_id,))
			
		else:
			# insert new router
			created = mysql.formatdt(statstime)
			#events = [] # don't fire sub-events of created events
			ru = router_update
			router_update["status"] = "online" # use 'online' here, as anything different is only evaluated if olddata is present
			mysql.execute("""
				INSERT INTO router (status, hostname, created, last_contact, sys_time, sys_uptime, sys_memfree, sys_membuff, sys_memcache,
				sys_loadavg, sys_procrun, sys_proctot, clients, clients_eth, clients_w2, clients_w5,
				w2_active, w2_busy, w5_active, w5_busy, w2_airtime, w5_airtime, wan_uplink, tc_enabled, tc_in, tc_out,
				cpu, chipset, hardware, os, babel_version,
				batman, routing_protocol, kernel, nodewatcher, firmware, firmware_rev, description, position_comment, community, hood, v2, local, gateway,
				status_text, contact, lng, lat, neighbors)
				VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			""",(
				ru["status"],ru["hostname"],created,ru["last_contact"],ru["sys_time"].strftime('%Y-%m-%d %H:%M:%S'),ru["sys_uptime"],ru["memory"]["free"],ru["memory"]["buffering"],ru["memory"]["caching"],
				ru["sys_loadavg"],ru["processes"]["runnable"],ru["processes"]["total"],ru["clients"],ru["clients_eth"],ru["clients_w2"],ru["clients_w5"],
				None,None,None,None,None,None,ru["has_wan_uplink"],ru["tc_enabled"],ru["tc_in"],ru["tc_out"],
				ru["cpu"],ru["chipset"],ru["hardware"],ru["os"],ru["babel_version"],
				ru["batman_adv"],ru["rt_protocol"],ru["kernel"],ru["nodewatcher"],ru["firmware"],ru["firmware_rev"],ru["description"],ru["position_comment"],ru["community"],ru["hoodid"],ru["v2"],ru["local"],ru["gateway"],
				ru["status_text"],ru["contact"],ru["lng"],ru["lat"],ru["visible_neighbours"],))
			router_id = mysql.cursor().lastrowid
			
			events_append(mysql,router_id,"created","")
		
		ndata = []
		adata = []
		for n in router_update["netifs"]:
			ndata.append((router_id,n["name"],n["mtu"],n["traffic"]["rx_bytes"],n["traffic"]["tx_bytes"],n["traffic"]["rx"],n["traffic"]["tx"],n["fe80_addr"],n["ipv4_addr"],n["mac"],n["wlan_channel"],n["wlan_type"],n["wlan_width"],n["wlan_ssid"],n["wlan_txpower"],))
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
			gwdata.append((router_id,g["mac"],g["quality"],g["nexthop"],g["netif"],g["gw_class"],g["selected"],))
		
		mysql.executemany("""
			INSERT INTO router_gw (router, mac, quality, nexthop, netif, gw_class, selected)
			VALUES (%s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE
				quality=VALUES(quality),
				nexthop=VALUES(nexthop),
				netif=VALUES(netif),
				gw_class=VALUES(gw_class),
				selected=VALUES(selected)
		""",gwdata)
		
		if router_id:
			new_router_stats(mysql, router_id, uptime, router_update, netifdict, statstime)
		
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
			#if (olddata["sys_uptime"] - 300) > router_update["sys_uptime"]:
			if olddata["sys_uptime"] > router_update["sys_uptime"]:
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
		UPDATE router_netif AS n
		INNER JOIN router AS r ON r.id = n.router
		SET n.rx = 0, n.tx = 0
		WHERE r.last_contact < %s AND r.status <> 'offline' AND r.status <> 'orphaned'
	""",(threshold,))
	# Online to Offline has to be updated after other queries!
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
		DELETE FROM router
		WHERE last_contact < %s AND status <> 'offline'
	""",(threshold,))
	mysql.commit()

def delete_unlinked_routers(mysql):
	# Delete entries in router_* tables without corresponding router in master table
	
	tables = ["router_events","router_gw","router_ipv6","router_neighbor","router_netif","router_stats","router_stats_gw","router_stats_neighbor","router_stats_netif","router_stats_old","router_stats_old_gw","router_stats_old_neighbor","router_stats_old_netif"]
	
	for t in tables:
		start_time = time.time()
		mysql.execute("""
			DELETE d FROM {} AS d
			LEFT JOIN router AS r ON r.id = d.router
			WHERE r.id IS NULL
		""".format(t))
		mysql.commit()
		#mysql.execute("""
		#	DELETE FROM {}
		#	WHERE {}.router NOT IN (
		#	SELECT id FROM router
		#	)
		#""".format(t,t))
		print("--- Deleted %i rows from %s: %.3f seconds ---" % (mysql.cursor().rowcount,t,time.time() - start_time))
		time.sleep(1)

def delete_stats_helper(mysql,label,query,tuple):
	minustime=0
	rowsaffected=1
	allrows=0
	start_time = time.time()
	while rowsaffected > 0:
		try:
			rowsaffected = mysql.execute(query,tuple)
			mysql.commit()
			allrows += rowsaffected
		except my.OperationalError:
			rowsaffected = 1
		time.sleep(10)
		minustime += 10
	end_time = time.time()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Deleted %i rows from %s stats: %.3f seconds" % (allrows,label,end_time - start_time - minustime))
	print("--- Deleted %i rows from %s stats: %.3f seconds ---" % (allrows,label,end_time - start_time - minustime))

def delete_old_stats(mysql):
	threshold			= (utcnow() - datetime.timedelta(days=CONFIG["router_stat_days"])).timestamp()
	threshold_netif		= (utcnow() - datetime.timedelta(days=CONFIG["router_stat_netif"])).timestamp()
	threshold_gw		= (utcnow() - datetime.timedelta(days=CONFIG["router_stat_gw"])).timestamp()
	threshold_gw_netif	= mysql.formatdt(utcnow() - datetime.timedelta(hours=CONFIG["gw_netif_threshold_hours"]))
	old					= (utcnow() - datetime.timedelta(days=CONFIG["router_oldstat_days"])).timestamp()
	old_netif			= (utcnow() - datetime.timedelta(days=CONFIG["router_oldstat_netif"])).timestamp()
	old_gw				= (utcnow() - datetime.timedelta(days=CONFIG["router_oldstat_gw"])).timestamp()

	limit = "100000"
	limit = "500000"

	start_time = time.time()
	rowsaffected = mysql.execute("""
		DELETE s FROM router_stats AS s
		LEFT JOIN router AS r ON s.router = r.id
		WHERE s.time < %s AND (r.status = 'online' OR r.status IS NULL)
	""",(threshold,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Deleted %i rows from stats: %.3f seconds" % (rowsaffected,time.time() - start_time))
	print("--- Deleted %i rows from stats: %.3f seconds ---" % (rowsaffected,time.time() - start_time))

	time.sleep(10)
	start_time = time.time()
	rowsaffected = mysql.execute("""
		DELETE s FROM router_stats_old AS s
		LEFT JOIN router AS r ON s.router = r.id
		WHERE s.time < %s AND (r.status = 'online' OR r.status IS NULL)
	""",(old,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Deleted %i rows from stats (old): %.3f seconds" % (rowsaffected,time.time() - start_time))
	print("--- Deleted %i rows from stats (old): %.3f seconds ---" % (rowsaffected,time.time() - start_time))

	time.sleep(10)
	query = """
				DELETE FROM router_stats_gw
				WHERE time < %s
				LIMIT """+limit+"""
			"""
	delete_stats_helper(mysql,"gw-stats",query,(threshold_gw,))

	time.sleep(10)
	query = """
				DELETE FROM router_stats_old_gw
				WHERE time < %s
				LIMIT """+limit+"""
			"""
	delete_stats_helper(mysql,"gw-stats (old)",query,(old_gw,))

	time.sleep(30)
	query = """
				DELETE FROM router_stats_neighbor
				WHERE time < %s
				LIMIT """+limit+"""
			"""
	delete_stats_helper(mysql,"neighbor-stats",query,(threshold,))

	time.sleep(30)
	query = """
				DELETE FROM router_stats_old_neighbor
				WHERE time < %s
				LIMIT """+limit+"""
			"""
	delete_stats_helper(mysql,"neighbor-stats (old)",query,(old,))

	time.sleep(30)
	query = """
				DELETE FROM router_stats_netif
				WHERE time < %s
				LIMIT """+limit+"""
			"""
	delete_stats_helper(mysql,"netif-stats",query,(threshold_netif,))

	time.sleep(30)
	query = """
				DELETE FROM router_stats_old_netif
				WHERE time < %s
				LIMIT """+limit+"""
			"""
	delete_stats_helper(mysql,"netif-stats (old)",query,(old_netif,))

	start_time = time.time()
	allrows = mysql.execute("DELETE FROM gw_netif WHERE last_contact < %s",(threshold_gw_netif,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Deleted %i rows from gw_netif: %.3f seconds" % (allrows,time.time() - start_time))
	print("--- Deleted %i rows from gw_netif: %.3f seconds ---" % (allrows,time.time() - start_time))

	time.sleep(10)
	start_time = time.time()
	allrows=0
	events = mysql.fetchall("""
		SELECT router, COUNT(time) AS count FROM router_events
		GROUP BY router
	""")
	
	for e in events:
		delnum = int(e["count"] - CONFIG["event_num_entries"])
		if delnum > 0:
			allrows += mysql.execute("""
				DELETE FROM router_events
				WHERE router = %s
				ORDER BY time ASC
				LIMIT %s
			""",(e["router"],delnum,))
	mysql.commit()
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Deleted %i rows from events: %.3f seconds" % (allrows,time.time() - start_time))
	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "-------")
	print("--- Deleted %i rows from events: %.3f seconds ---" % (allrows,time.time() - start_time))

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

def new_router_stats(mysql, router_id, uptime, router_update, netifdict, statstime):
	#if not (uptime + CONFIG["router_stat_mindiff_secs"]) < router_update["sys_uptime"]:
	#	return
	time = mysql.formattimestamp(statstime)

	stattime = mysql.findone("SELECT time FROM router_stats WHERE router = %s ORDER BY time DESC LIMIT 1",(router_id,),"time")
	oldstattime = mysql.findone("SELECT time FROM router_stats_old WHERE router = %s ORDER BY time DESC LIMIT 1",(router_id,),"time")

	routerdata = (
		time,
		router_id,
		router_update["memory"]['free'],
		router_update["memory"]['buffering'],
		router_update["memory"]['caching'],
		router_update["sys_loadavg"],
		router_update["processes"]['runnable'],
		router_update["processes"]['total'],
		router_update["clients"],
		router_update["clients_eth"],
		router_update["clients_w2"],
		router_update["clients_w5"],
		router_update["w2_airtime"],
		router_update["w5_airtime"],
		)

	if not stattime or (stattime + CONFIG["router_stat_mindiff_default"]) < time:
		mysql.execute("""
			INSERT INTO router_stats (time, router, sys_memfree, sys_membuff, sys_memcache, loadavg, sys_procrun, sys_proctot,
			clients, clients_eth, clients_w2, clients_w5, airtime_w2, airtime_w5)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
		""",routerdata)
	if not oldstattime or (oldstattime + CONFIG["router_oldstat_mindiff_default"]) < time:
		mysql.execute("""
			INSERT INTO router_stats_old (time, router, sys_memfree, sys_membuff, sys_memcache, loadavg, sys_procrun, sys_proctot,
			clients, clients_eth, clients_w2, clients_w5, airtime_w2, airtime_w5)
			VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
		""",routerdata)
	
	netiftime = mysql.findone("SELECT time FROM router_stats_netif WHERE router = %s ORDER BY time DESC LIMIT 1",(router_id,),"time")
	oldnetiftime = mysql.findone("SELECT time FROM router_stats_old_netif WHERE router = %s ORDER BY time DESC LIMIT 1",(router_id,),"time")

	ndata = []
	nkeys = []
	for netif in router_update["netifs"]:
		# sanitize name
		name = netif["name"].replace(".", "").replace("$", "")
		with suppress(KeyError):
			if name in netifdict.keys():
				ndata.append((time,router_id,netifdict[name],netif["traffic"]["rx"],netif["traffic"]["tx"],))
			else:
				writelog(CONFIG["debug_dir"] + "/test_yellow.txt", "{}".format(name))
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

	if not netiftime or (netiftime + CONFIG["router_stat_mindiff_netif"]) < time:
		mysql.executemany("""
			INSERT INTO router_stats_netif (time, router, netif, rx, tx)
			VALUES (%s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
		""",ndata)
	if not oldnetiftime or (oldnetiftime + CONFIG["router_oldstat_mindiff_netif"]) < time:
		mysql.executemany("""
			INSERT INTO router_stats_old_netif (time, router, netif, rx, tx)
			VALUES (%s, %s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
		""",ndata)

	# reuse timestamp from router_stats to avoid additional queries
	nbdata = []
	for neighbour in router_update["neighbours"]:
		with suppress(KeyError):
			nbdata.append((time,router_id,neighbour["mac"],neighbour["quality"],))
	if not stattime or (stattime + CONFIG["router_stat_mindiff_default"]) < time:
		mysql.executemany("""
			INSERT INTO router_stats_neighbor (time, router, mac, quality)
			VALUES (%s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
		""",nbdata)
	if not oldstattime or (oldstattime + CONFIG["router_oldstat_mindiff_default"]) < time:
		 mysql.executemany("""
			INSERT INTO router_stats_old_neighbor (time, router, mac, quality)
			VALUES (%s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
		""",nbdata)

	# reuse timestamp from router_stats to avoid additional queries
	gwdata = []
	for gw in router_update["gws"]:
		with suppress(KeyError):
			gwdata.append((time,router_id,gw["mac"],gw["quality"],))
	if not stattime or (stattime + CONFIG["router_stat_mindiff_default"]) < time:
		mysql.executemany("""
			INSERT INTO router_stats_gw (time, router, mac, quality)
			VALUES (%s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
		""",gwdata)
	if not oldstattime or (oldstattime + CONFIG["router_oldstat_mindiff_default"]) < time:
		mysql.executemany("""
			INSERT INTO router_stats_old_gw (time, router, mac, quality)
			VALUES (%s, %s, %s, %s)
			ON DUPLICATE KEY UPDATE time=time
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
		# prevent division-by-zero error
		elif router_update["sys_uptime"] > 0:
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

def evalxpathbool(tree,p,default=False):
	tmp = default
	with suppress(IndexError):
		tmp = tree.xpath(p)[0]
	if tmp:
		return (tmp.lower()=="true" or tmp=="1")
	return default

def parse_nodewatcher_xml(xml,statstime):
	try:
		assert xml != ""
		tree = lxml.etree.fromstring(xml)

		router_update = {
			"status": evalxpath(tree,"/data/system_data/status/text()"),
			"hostname": evalxpath(tree,"/data/system_data/hostname/text()"),
			"last_contact": statstime.strftime('%Y-%m-%d %H:%M:%S'),
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
			"hood": evalxpath(tree,"/data/system_data/hood/text()",None), # return None if not present and "" if empty => distinction between V1 and V2 with no hood
			"status_text": evalxpath(tree,"/data/system_data/status_text/text()"),
			"contact": evalxpath(tree,"/data/system_data/contact/text()"),
			# system
			"sys_time": datetime.datetime.fromtimestamp(evalxpathint(tree,"/data/system_data/local_time/text()")),
			"sys_uptime": int(evalxpathfloat(tree,"/data/system_data/uptime/text()")),
			"memory": {
				"free": evalxpathint(tree,"/data/system_data/memory_free/text()"),
				"buffering": evalxpathint(tree,"/data/system_data/memory_buffering/text()"),
				"caching": evalxpathint(tree,"/data/system_data/memory_caching/text()"),
			},
			"clients": evalxpathint(tree,"/data/client_count/text()"),
			"clients_eth": evalxpathint(tree,"/data/clients/*[starts-with(name(), 'eth')]/text()",None),
			"clients_w2": evalxpathint(tree,"/data/clients/w2ap/text()",None),
			"clients_w5": evalxpathint(tree,"/data/clients/w5ap/text()",None),
			"w2_busy": evalxpathint(tree,"/data/airtime2/busy/text()",None),
			"w2_active": evalxpathint(tree,"/data/airtime2/active/text()",None),
			"w5_busy": evalxpathint(tree,"/data/airtime5/busy/text()",None),
			"w5_active": evalxpathint(tree,"/data/airtime5/active/text()",None),
			"has_wan_uplink": (
				(len(tree.xpath("/data/system_data/vpn_active")) > 0
				and evalxpathint(tree,"/data/system_data/vpn_active/text()") == 1)
				or len(tree.xpath("/data/interface_data/%s" % CONFIG["vpn_netif"])) > 0
				or len(tree.xpath("/data/interface_data/*[starts-with(name(), '%s')]" % CONFIG["vpn_netif_l2tp"])) > 0
				or len(tree.xpath("/data/interface_data/%s" % CONFIG["vpn_netif_aux"])) > 0),
			"tc_enabled": evalxpathbool(tree,"/data/traffic_control/wan/enabled/text()",None),
			"tc_in": evalxpathfloat(tree,"/data/traffic_control/wan/in/text()",None),
			"tc_out": evalxpathfloat(tree,"/data/traffic_control/wan/out/text()",None),
			# software
			"os": "%s (%s)" % (evalxpath(tree,"/data/system_data/distname/text()"),
					   evalxpath(tree,"/data/system_data/distversion/text()")),
			"babel_version": evalxpath(tree,"/data/system_data/babel_version/text()"),
			"batman_adv": evalxpath(tree,"/data/system_data/batman_advanced_version/text()"),
			"rt_protocol": evalxpath(tree,"/data/system_data/rt_protocol/text()",None),
			"kernel": evalxpath(tree,"/data/system_data/kernel_version/text()"),
			"nodewatcher": evalxpath(tree,"/data/system_data/nodewatcher_version/text()"),
			#"fastd": evalxpath(tree,"/data/system_data/fastd_version/text()"),
			"firmware": evalxpath(tree,"/data/system_data/firmware_version/text()"),
			"firmware_rev": evalxpath(tree,"/data/system_data/firmware_revision/text()"),
		}

		router_update["v2"] = bool(router_update["hood"] is not None) # None = V1, "" or content = V2

		loadavg = evalxpathfloat(tree,"/data/system_data/loadavg/text()",None)
		if not loadavg == None:
			router_update["sys_loadavg"] = loadavg
		else:
			router_update["sys_loadavg"] = evalxpathfloat(tree,"/data/system_data/loadavg5/text()")

		processboth = evalxpath(tree,"/data/system_data/processes/text()")
		router_update["processes"] = {}
		if processboth:
			router_update["processes"]["runnable"] = int(processboth.split("/")[0])
			router_update["processes"]["total"] = int(processboth.split("/")[1])
		else:
			router_update["processes"]["runnable"] = 0
			router_update["processes"]["total"] = 0

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
				"ipv4_addr": ipv4toint(evalxpath(netif,"ipv4_addr/text()")),
				"mac": mac2int(evalxpath(netif,"mac_addr/text()")),
				"wlan_channel": evalxpathint(netif,"wlan_channel/text()",None),
				"wlan_type": evalxpath(netif,"wlan_type/text()",None),
				"wlan_width": evalxpathint(netif,"wlan_width/text()",None),
				"wlan_ssid": evalxpath(netif,"wlan_ssid/text()",None),
				"wlan_txpower": evalxpath(netif,"wlan_tx_power/text()",None),
			}
			with suppress(IndexError):
				interface["fe80_addr"] = None
				interface["fe80_addr"] = ipv6tobin(netif.xpath("ipv6_link_local_addr/text()")[0].split("/")[0])
			interface["ipv6_addrs"] = []
			if len(netif.xpath("ipv6_addr/text()")) > 0:
				for ipv6_addr in netif.xpath("ipv6_addr/text()"):
					interface["ipv6_addrs"].append(ipv6tobinmasked(ipv6_addr.split("/")[0]))

			router_update["netifs"].append(interface)

		visible_neighbours = 0

		for originator in tree.xpath("/data/batman_adv_originators/*"):
			visible_neighbours += 1
			o_mac = mac2int(evalxpath(originator,"originator/text()"))
			o_nexthop = mac2int(evalxpath(originator,"nexthop/text()"))
			# mac is the mac of the neighbour w2/5mesh if
			# (which might also be called wlan0-1)
			o_out_if = evalxpath(originator,"outgoing_interface/text()")
			if o_mac == o_nexthop:
				# skip vpn server
				if o_out_if == CONFIG["vpn_netif"]:
					continue
				elif o_out_if.startswith(CONFIG["vpn_netif_l2tp"]):
					continue
				elif o_out_if == CONFIG["vpn_netif_aux"]:
					continue
				neighbour = {
					"mac": o_mac,
					"netif": o_out_if,
					"quality": evalxpathfloat(originator,"link_quality/text()"),
					"type": "l2"
				}
				router_update["neighbours"].append(neighbour)

		l3_neighbours = get_l3_neighbours(tree)
		visible_neighbours += len(l3_neighbours)
		router_update["visible_neighbours"] = visible_neighbours
		router_update["neighbours"] += l3_neighbours
		
		router_update["gateway"] = False # Default: false
		for gw in tree.xpath("/data/batman_adv_gateway_list/*"):
			gw_mac = evalxpath(gw,"gateway/text()")
			if (gw_mac and len(gw_mac)>12): # Throw away headline
				if len(gw_mac) > 17:
					gw_mac = gw_mac[0:17]
				gw = {
					"mac": mac2int(gw_mac),
					"quality": evalxpath(gw,"link_quality/text()"),
					"nexthop": mac2int(evalxpath(gw,"nexthop/text()",None)),
					"netif": evalxpath(gw,"outgoing_interface/text()",None),
					"gw_class": evalxpath(gw,"gw_class/text()",None),
					"selected": evalxpathbool(gw,"selected/text()")
				}
				if gw["netif"]=="internal":
					router_update["gateway"] = True # If "internal" exists, device must be a gateway
				if gw["quality"].startswith("false"):
					gw["quality"] = gw["quality"][5:]
				if gw["quality"]:
					gw["quality"] = float(gw["quality"])
				else:
					gw["quality"] = 0
				if gw["netif"]=="false":
					tmp = gw["gw_class"].split(None,1)
					gw["netif"] = tmp[0]
					gw["gw_class"] = tmp[1]
				router_update["gws"].append(gw)

		if not router_update["gws"]:
			# Only change if list is empty (this will keep previously set value in all other cases)
			router_update["gateway"] = True

		return router_update
	except (AssertionError, lxml.etree.XMLSyntaxError, IndexError) as e:
		raise ValueError("%s: %s" % (e.__class__.__name__, str(e)))

def get_l3_neighbours(tree):
	l3_neighbours = list()
	for neighbour in tree.xpath("/data/babel_neighbours/*"):
		iptmp = evalxpath(neighbour,"ip/text()",None)
		if not iptmp:
			iptmp = neighbour.text
		neighbour = {
			"mac": mac2int(get_mac_from_v6_link_local(iptmp)),
			"netif": neighbour.xpath("outgoing_interface/text()")[0],
			"quality": -1.0*evalxpathfloat(neighbour,"link_cost/text()",1),
			"type": "l3"
		}
		l3_neighbours.append(neighbour)
	return l3_neighbours

def get_mac_from_v6_link_local(v6_fe80):
	fullip = ipaddress.ip_address(v6_fe80).exploded
	first = '%02x' % (int(fullip[20:22], 16) ^ 2)
	mac = (first,fullip[22:24],fullip[25:27],fullip[32:34],fullip[35:37],fullip[37:39],)
	return ':'.join(mac)
