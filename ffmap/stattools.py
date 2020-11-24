#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL
from ffmap.influxtools import FreifunkInflux
from ffmap.gwtools import gw_name, gw_bat
from ffmap.misc import *
from ffmap.config import CONFIG

from collections import OrderedDict

def total_clients(mysql,selecthood=None):
	if selecthood:
		return mysql.findone("""
			SELECT SUM(clients) AS clients
			FROM router
			WHERE hood = %s
		""",(selecthood,),"clients")
	else:
		return mysql.findone("""
			SELECT SUM(clients) AS clients
			FROM router
		""",(),"clients")

def router_status(mysql,selecthood=None):
	if selecthood:
		tmp = mysql.fetchdict("""
			SELECT status, COUNT(id) AS count
			FROM router
			WHERE hood = %s
			GROUP BY status
		""",(selecthood,),"status","count")
	else:
		tmp = mysql.fetchdict("""
			SELECT status, COUNT(id) AS count
			FROM router
			GROUP BY status
		""",(),"status","count")
	tmp["sum"] = sum(tmp.values())
	return tmp

def router_traffic(mysql,selecthood=None):
	# rx and tx are exchanged for bat0, since we want to get client traffic, which is the mirror of bat0 traffic
	if selecthood:
		tmp = mysql.findone("""
			SELECT SUM(rx) AS tx, SUM(tx) AS rx FROM router_netif
			INNER JOIN router ON router_netif.router = router.id
			WHERE hood = %s AND gateway = FALSE AND netif = 'bat0'
		""",(selecthood,))
		gw = mysql.findone("""
			SELECT SUM(rx) AS rx, SUM(tx) AS tx FROM router_netif
			INNER JOIN router ON router_netif.router = router.id
			WHERE hood = %s AND gateway = TRUE AND netif IN ('eth0.1','eth1.1','w2ap','w5ap')
		""",(selecthood,))
	else:
		tmp = mysql.findone("""
			SELECT SUM(rx) AS tx, SUM(tx) AS rx FROM router_netif
			INNER JOIN router ON router_netif.router = router.id
			WHERE gateway = FALSE AND netif = 'bat0'
		""",())
		gw = mysql.findone("""
			SELECT SUM(rx) AS rx, SUM(tx) AS tx FROM router_netif
			INNER JOIN router ON router_netif.router = router.id
			WHERE gateway = TRUE AND netif IN ('eth0.1','eth1.1','w2ap','w5ap')
		""",())
	if "rx" in gw and gw["rx"]:
		tmp["rx"] += gw["rx"]
	if "tx" in gw and gw["tx"]:
		tmp["tx"] += gw["tx"]
	return tmp

def total_clients_hood(mysql):
	return mysql.fetchdict("""
		SELECT hood, SUM(clients) AS clients
		FROM router
		GROUP BY hood
	""",(),"hood","clients")

def router_status_hood(mysql):
	data = mysql.fetchall("""
		SELECT hood, status, COUNT(id) AS count
		FROM router
		GROUP BY hood, status
	""")
	dict = {}
	for d in data:
		if not d["hood"] in dict:
			dict[d["hood"]] = {}
		dict[d["hood"]][d["status"]] = d["count"]
	return dict

def router_traffic_hood(mysql):
	# rx and tx are exchanged for bat0, since we want to get client traffic, which is the mirror of bat0 traffic
	dict = mysql.fetchdict("""
		SELECT hood, SUM(rx) AS tx, SUM(tx) AS rx FROM router_netif
		INNER JOIN router ON router_netif.router = router.id
		WHERE gateway = FALSE AND netif = 'bat0'
		GROUP BY hood
	""",(),"hood")
	gw = mysql.fetchall("""
		SELECT hood, SUM(rx) AS rx, SUM(tx) AS tx FROM router_netif
		INNER JOIN router ON router_netif.router = router.id
		WHERE gateway = TRUE AND netif IN ('eth0.1','eth1.1','w2ap','w5ap')
		GROUP BY hood
	""")
	allhoods = mysql.fetchall("""
		SELECT hood
		FROM router
		GROUP BY hood
	""")
	for d in gw:
		if not d["hood"] in dict:
			dict[d["hood"]] = d
		else:
			dict[d["hood"]]["rx"] += d["rx"]
			dict[d["hood"]]["tx"] += d["tx"]
	for h in allhoods:
		if not h["hood"] in dict:
			dict[h["hood"]] =  {"hood": h["hood"], "rx": int(0), "tx": int(0)}
	return dict

def total_clients_gw(mysql):
	return mysql.fetchdict("""
		SELECT router_gw.mac, SUM(clients) AS clients
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		WHERE router_gw.selected = TRUE
		GROUP BY router_gw.mac
	""",(),"mac","clients")

def router_status_gw(mysql):
	data = mysql.fetchall("""
		SELECT router_gw.mac, router.status, COUNT(router_gw.router) AS count
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		WHERE router_gw.selected = TRUE
		GROUP BY router_gw.mac, router.status
	""")
	dict = {}
	for d in data:
		if not d["mac"] in dict:
			dict[d["mac"]] = {}
		dict[d["mac"]][d["status"]] = d["count"]
	return dict

def router_models(mysql,selecthood=None,selectgw=None):
	if selecthood:
		return mysql.fetchdict("""
			SELECT hardware, COUNT(id) AS count, SUM(clients) AS clients
			FROM router
			WHERE hood = %s
			GROUP BY hardware
			ORDER BY hardware
		""",(selecthood,),"hardware")
	elif selectgw:
		return mysql.fetchdict("""
			SELECT hardware, COUNT(router_gw.router) AS count, SUM(clients) AS clients
			FROM router
			INNER JOIN router_gw ON router.id = router_gw.router
			WHERE mac = %s
			GROUP BY hardware
			ORDER BY hardware
		""",(mac2int(selectgw),),"hardware")
	else:
		return mysql.fetchdict("""
			SELECT hardware, COUNT(id) AS count, SUM(clients) AS clients
			FROM router
			GROUP BY hardware
			ORDER BY hardware
		""",(),"hardware")

def router_firmwares(mysql,selecthood=None,selectgw=None):
	if selecthood:
		return mysql.fetchdict("""
			SELECT firmware, COUNT(id) AS count
			FROM router
			WHERE hood = %s
			GROUP BY firmware
			ORDER BY firmware
		""",(selecthood,),"firmware","count")
	elif selectgw:
		return mysql.fetchdict("""
			SELECT firmware, COUNT(router_gw.router) AS count
			FROM router
			INNER JOIN router_gw ON router.id = router_gw.router
			WHERE mac = %s
			GROUP BY firmware
			ORDER BY firmware
		""",(mac2int(selectgw),),"firmware","count")
	else:
		return mysql.fetchdict("""
			SELECT firmware, COUNT(id) AS count
			FROM router
			GROUP BY firmware
			ORDER BY firmware
		""",(),"firmware","count")

def hoods(mysql,selectgw=None):
	data = mysql.fetchall("""
		SELECT hoods.id AS hoodid, hoods.name AS hood, status, COUNT(router.id) AS count
		FROM router
		LEFT JOIN hoods ON router.hood = hoods.id
		GROUP BY hoods.id, hoods.name, status
		ORDER BY hoods.name
	""")
	result = {}
	for rs in data:
		if not rs["hood"]:
			rs["hoodid"] = 1
			rs["hood"] = "NoHood"
		if not rs["hoodid"] in result:
			result[rs["hoodid"]] = {'name':rs["hood"]}
		result[rs["hoodid"]][rs["status"]] = rs["count"]
	return result

def hoods_sum(mysql,selectgw=None):
	data = mysql.fetchall("""
		SELECT hood, COUNT(id) AS count, SUM(clients) AS clients, MAX(v2) AS v2, MAX(local) AS local
		FROM router
		GROUP BY hood
	""")
	result = {}
	for rs in data:
		if not rs["hood"]:
			rs["hood"] = "Default"
		result[rs["hood"]] = {"routers": rs["count"], "clients": rs["clients"], "v2": rs["v2"], "local": rs["local"]}
	return result

def hoods_gws(mysql):
	data = mysql.fetchall("""
		SELECT hood, COUNT(sub.mac) AS count
		FROM (
			SELECT hood, router_gw.mac, COUNT(router.id) AS routers
			FROM router
			INNER JOIN router_gw ON router.id = router_gw.router
			WHERE router.status = 'online'
			GROUP BY hood, router_gw.mac
		) AS sub
		WHERE routers > 1
		GROUP BY hood
	""")
	result = {}
	for rs in data:
		if not rs["hood"]:
			rs["hood"] = "Default"
		result[rs["hood"]] = rs["count"]
	return result

def gateways(mysql):
	macs = mysql.fetchall("""
		SELECT router_gw.mac, gw.name, gw.id AS gw, gw.version, gw_netif.netif
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		LEFT JOIN (gw_netif INNER JOIN gw ON gw_netif.gw = gw.id)
		ON router_gw.mac = gw_netif.mac
		WHERE router.status <> 'orphaned' AND NOT ISNULL(gw.name)
		GROUP BY router_gw.mac
		ORDER BY gw.name ASC, gw_netif.netif ASC, router_gw.mac ASC
	""")
	selected = mysql.fetchall("""
		SELECT gw_netif.gw, router.status, COUNT(router_gw.router) AS count
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		INNER JOIN gw_netif ON gw_netif.mac = router_gw.mac
		WHERE router_gw.selected = TRUE AND router.status <> 'orphaned'
		GROUP BY gw_netif.gw, router.status
	""")
	others = mysql.fetchall("""
		SELECT gw_netif.gw, router.status, COUNT(router_gw.router) AS count
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		INNER JOIN gw_netif ON gw_netif.mac = router_gw.mac
		WHERE router_gw.selected = FALSE AND router.status <> 'orphaned'
		GROUP BY gw_netif.gw, router.status
	""")
	
	result = OrderedDict()
	for m in macs:
		if not m["gw"] in result:
			result[m["gw"]] = {"name":m["name"],"version":m["version"],"macs":[],"selected":{},"others":{}}
		result[m["gw"]]["macs"].append(m["mac"])
	for rs in selected:
		result[rs["gw"]]["selected"][rs["status"]] = rs["count"]
	for rs in others:
		result[rs["gw"]]["others"][rs["status"]] = rs["count"]
	return result

def gws_ipv4(mysql):
	data = mysql.fetchall("""
		SELECT name, n1.ipv4, n1.netif AS batif, n2.netif AS vpnif, n2.mac FROM gw
		INNER JOIN gw_netif AS n1 ON gw.id = n1.gw
		LEFT JOIN gw_netif AS n2 ON n2.mac = n1.vpnmac AND n1.gw = n2.gw
		WHERE n1.ipv4 IS NOT NULL
		GROUP BY name, n1.ipv4, n1.netif, n2.netif, n2.mac
		ORDER BY n1.ipv4
	""")
	
	return data

def gws_ipv6(mysql):
	data = mysql.fetchall("""
		SELECT name, n1.ipv6, n1.netif AS batif, n2.netif AS vpnif, n2.mac FROM gw
		INNER JOIN gw_netif AS n1 ON gw.id = n1.gw
		LEFT JOIN gw_netif AS n2 ON n2.mac = n1.vpnmac AND n1.gw = n2.gw
		WHERE n1.ipv6 IS NOT NULL
		GROUP BY name, n1.ipv6, n1.netif, n2.netif, n2.mac
		ORDER BY n1.ipv6
	""")
	
	return data

def gws_dhcp(mysql):
	data = mysql.fetchall("""
		SELECT name, n1.dhcpstart, n1.dhcpend, n1.netif AS batif, n2.netif AS vpnif, n2.mac FROM gw
		INNER JOIN gw_netif AS n1 ON gw.id = n1.gw
		LEFT JOIN gw_netif AS n2 ON n2.mac = n1.vpnmac AND n1.gw = n2.gw
		WHERE n1.dhcpstart IS NOT NULL
		GROUP BY name, n1.dhcpstart, n1.dhcpend, n1.netif, n2.netif, n2.mac
		ORDER BY n1.dhcpstart
	""")
	
	return data

def gws_ifs(mysql,selecthood=None):
	if selecthood:
		where = " AND hood=%s"
		tup = (selecthood,)
	else:
		where = ""
		tup = ()
	
	macs = mysql.fetchall("""
		SELECT router_gw.mac, CONCAT(ISNULL(gw.name),'-',IF(NOT ISNULL(gw.name),CONCAT(gw.name,'-',gw_netif.netif),router_gw.mac)) AS sort
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		LEFT JOIN (gw_netif INNER JOIN gw ON gw_netif.gw = gw.id)
		ON router_gw.mac = gw_netif.mac
		WHERE router.status <> 'orphaned' {}
		GROUP BY router_gw.mac
		ORDER BY ISNULL(gw.name), gw.name ASC, gw_netif.netif ASC, router_gw.mac ASC
	""".format(where),tup)
	selected = mysql.fetchall("""
		SELECT router_gw.mac, router.status, COUNT(router_gw.router) AS count
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		WHERE router_gw.selected = TRUE AND router.status <> 'orphaned' {}
		GROUP BY router_gw.mac, router.status
	""".format(where),tup)
	others = mysql.fetchall("""
		SELECT router_gw.mac, router.status, COUNT(router_gw.router) AS count
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		WHERE router_gw.selected = FALSE AND router.status <> 'orphaned' {}
		GROUP BY router_gw.mac, router.status
	""".format(where),tup)
	
	result = OrderedDict()
	for m in macs:
		result[m["mac"]] = {"selected":{},"others":{},"sort":m["sort"]}
	for rs in selected:
		result[rs["mac"]]["selected"][rs["status"]] = rs["count"]
	for rs in others:
		result[rs["mac"]]["others"][rs["status"]] = rs["count"]
	return result

def gws_sum(mysql,selecthood=None):
	if selecthood:
		where = " AND hood=%s"
		tup = (selecthood,)
	else:
		where = ""
		tup = ()
	
	data = mysql.fetchall("""
		SELECT router_gw.mac, COUNT(router_gw.router) AS count, SUM(router.clients) AS clients
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		WHERE router_gw.selected = TRUE AND router.status <> 'orphaned' {}
		GROUP BY router_gw.mac
	""".format(where),tup)
	result = {}
	for rs in data:
		result[rs["mac"]] = {"routers": rs["count"], "clients": rs["clients"]}
	return result

def gws_info(mysql,selecthood=None):
	if selecthood:
		where = "WHERE hood=%s"
		tup = (selecthood,)
	else:
		where = ""
		tup = ()
	
	data = mysql.fetchdict("""
		SELECT router_gw.mac AS mac, gw.name AS gw, stats_page, version, n1.netif AS gwif, n2.netif AS batif, n2.mac AS batmac, n2.ipv4 AS ipv4, n2.ipv6 AS ipv6, n2.dhcpstart AS dhcpstart, n2.dhcpend AS dhcpend
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		LEFT JOIN (
			gw_netif AS n1
			INNER JOIN gw ON n1.gw = gw.id
			LEFT JOIN gw_netif AS n2 ON n1.mac = n2.vpnmac AND n1.gw = n2.gw
		) ON router_gw.mac = n1.mac
		{}
		GROUP BY router_gw.mac, n2.netif, n2.mac
	""".format(where),tup,"mac")
	for d in data.values():
		d["label"] = gw_name(d)
		d["batX"] = gw_bat(d)
	return data

def gws_admin(mysql,selectgw):
	if not selectgw:
		return None
	
	data = mysql.fetchall("""
		SELECT gw_admin.name
		FROM gw_netif
		INNER JOIN gw_admin ON gw_netif.gw = gw_admin.gw
		WHERE mac = %s
		ORDER BY prio ASC
	""",(mac2int(selectgw),),"name")
	return data

def record_global_stats(influ,mysql):
	#threshold=(utcnow() - datetime.timedelta(days=CONFIG["global_stat_days"])).timestamp()
	time = influ.utctimestamp()
	status = router_status(mysql)
	traffic = router_traffic(mysql)

	stats_json = [{
		"measurement": "stat",
		"time": time,
		"fields": {
			"clients": int(total_clients(mysql)),
			"online": int(status.get("online",0)),
			"offline": int(status.get("offline",0)),
			"unknown": int(status.get("unknown",0)),
			"orphaned": int(status.get("orphaned",0)),
			"rx": int(traffic["rx"]),
			"tx": int(traffic["tx"])
			}
		}]

	influ.write(stats_json,"global_default")

def record_hood_stats(influ,mysql):
	#threshold=(utcnow() - datetime.timedelta(days=CONFIG["global_stat_days"])).timestamp()
	time = influ.utctimestamp()
	status = router_status_hood(mysql)
	clients = total_clients_hood(mysql)
	traffic = router_traffic_hood(mysql)

	stats_json = []
	for hood in clients.keys():
		if not hood:
			hood = 1

		stats_json.append({
			"measurement": "stat",
			"tags": {
				"hood": hood,
				},
			"time": time,
			"fields": {
				"clients": int(clients[hood]),
				"online": int(status[hood].get("online",0)),
				"offline": int(status[hood].get("offline",0)),
				"unknown": int(status[hood].get("unknown",0)),
				"orphaned": int(status[hood].get("orphaned",0)),
				"rx": int(traffic[hood]["rx"]),
				"tx": int(traffic[hood]["tx"])
				}
			})

	influ.write(stats_json,"global_hoods")

def record_gw_stats(influ,mysql):
	#threshold=(utcnow() - datetime.timedelta(days=CONFIG["global_gwstat_days"])).timestamp()
	time = influ.utctimestamp()
	status = router_status_gw(mysql)
	clients = total_clients_gw(mysql)

	stats_json = []
	for mac in clients.keys():
		stats_json.append({
			"measurement": "stat",
			"tags": {
				"mac": int2shortmac(mac),
				},
			"time": time,
			"fields": {
				"clients": int(clients[mac]),
				"online": int(status[mac].get("online",0)),
				"offline": int(status[mac].get("offline",0)),
				"unknown": int(status[mac].get("unknown",0)),
				"orphaned": int(status[mac].get("orphaned",0))
				}
			})

	influ.write(stats_json,"global_gw")

def router_user_sum(mysql):
	data = mysql.fetchall("""
		SELECT contact, COUNT(id) AS count, SUM(clients) AS clients
		FROM router
		GROUP BY contact
	""")
	result = {}
	for rs in data:
		if rs["contact"]:
			result[rs["contact"].lower()] = {"routers": rs["count"], "clients": rs["clients"]}
	return result
