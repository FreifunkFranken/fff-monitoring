#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL
from ffmap.misc import *
from ffmap.config import CONFIG

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

def router_models(mysql,selecthood=None):
	if selecthood:
		return mysql.fetchdict("""
			SELECT hardware, COUNT(id) AS count
			FROM router
			WHERE hood = %s
			GROUP BY hardware
		""",(selecthood,),"hardware","count")
	else:
		return mysql.fetchdict("""
			SELECT hardware, COUNT(id) AS count
			FROM router
			GROUP BY hardware
		""",(),"hardware","count")

def router_firmwares(mysql,selecthood=None):
	if selecthood:
		return mysql.fetchdict("""
			SELECT firmware, COUNT(id) AS count
			FROM router
			WHERE hood = %s
			GROUP BY firmware
		""",(selecthood,),"firmware","count")
	else:
		return mysql.fetchdict("""
			SELECT firmware, COUNT(id) AS count
			FROM router
			GROUP BY firmware
		""",(),"firmware","count")

def hoods(mysql):
	data = mysql.fetchall("""
		SELECT hood, status, COUNT(id) AS count
		FROM router
		GROUP BY hood, status
	""")
	result = {}
	for rs in data:
		if not rs["hood"]:
			rs["hood"] = "Default"
		if not rs["hood"] in result:
			result[rs["hood"]] = {}
		result[rs["hood"]][rs["status"]] = rs["count"]
	return result

def hoods_sum(mysql):
	data = mysql.fetchall("""
		SELECT hood, COUNT(id) AS count, SUM(clients) AS clients
		FROM router
		GROUP BY hood
	""")
	result = {}
	for rs in data:
		if not rs["hood"]:
			rs["hood"] = "Default"
		result[rs["hood"]] = {"routers": rs["count"], "clients": rs["clients"]}
	return result

def gws(mysql,selecthood=None):
	if selecthood:
		where = " AND hood=%s"
		tup = (selecthood,)
	else:
		where = ""
		tup = ()
	
	selected = mysql.fetchall("""
		SELECT router_gw.mac, router.status, COUNT(router_gw.router) AS count
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		WHERE router_gw.selected = TRUE {}
		GROUP BY router_gw.mac, router.status
	""".format(where),tup)
	others = mysql.fetchall("""
		SELECT router_gw.mac, router.status, COUNT(router_gw.router) AS count
		FROM router
		INNER JOIN router_gw ON router.id = router_gw.router
		WHERE router_gw.selected = FALSE {}
		GROUP BY router_gw.mac, router.status
	""".format(where),tup)
	result = {}
	for rs in selected:
		if not rs["mac"] in result:
			result[rs["mac"]] = {"selected":{},"others":{}}
		result[rs["mac"]]["selected"][rs["status"]] = rs["count"]
	for rs in others:
		if not rs["mac"] in result:
			result[rs["mac"]] = {"selected":{},"others":{}}
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
		WHERE router_gw.selected = TRUE {}
		GROUP BY router_gw.mac
	""".format(where),tup)
	result = {}
	for rs in data:
		result[rs["mac"]] = {"routers": rs["count"], "clients": rs["clients"]}
	return result

def record_global_stats(mysql):
	threshold=(utcnow() - datetime.timedelta(days=CONFIG["global_stat_days"])).timestamp()
	time = mysql.utctimestamp()
	status = router_status(mysql)
	
	old = mysql.findone("SELECT time FROM stats_global WHERE time = %s LIMIT 1",(time,))
	
	if old:
		mysql.execute("""
			UPDATE stats_global
			SET clients = %s, online = %s, offline = %s, unknown = %s, orphaned = %s
			WHERE time = %s
		""",(total_clients(mysql),status.get("online",0),status.get("offline",0),status.get("unknown",0),status.get("orphaned",0),time,))
	else:
		mysql.execute("""
			INSERT INTO stats_global (time, clients, online, offline, unknown, orphaned)
			VALUES (%s, %s, %s, %s, %s, %s)
		""",(time,total_clients(mysql),status.get("online",0),status.get("offline",0),status.get("unknown",0),status.get("orphaned",0),))
	
	mysql.execute("""
		DELETE FROM stats_global
		WHERE time < %s
	""",(threshold,))

	mysql.commit()

def record_hood_stats(mysql):
	threshold=(utcnow() - datetime.timedelta(days=CONFIG["global_stat_days"])).timestamp()
	time = mysql.utctimestamp()
	status = router_status_hood(mysql)
	clients = total_clients_hood(mysql)
	
	for hood in clients.keys():
		if not hood:
			hood = "Default"
		
		old = mysql.findone("SELECT time FROM stats_hood WHERE time = %s AND hood = %s LIMIT 1",(time,hood,))
		
		if old:
			mysql.execute("""
				UPDATE stats_hood
				SET clients = %s, online = %s, offline = %s, unknown = %s, orphaned = %s
				WHERE time = %s AND hood = %s
			""",(clients[hood],status[hood].get("online",0),status[hood].get("offline",0),status[hood].get("unknown",0),status[hood].get("orphaned",0),time,hood,))
		else:
			mysql.execute("""
				INSERT INTO stats_hood (time, hood, clients, online, offline, unknown, orphaned)
				VALUES (%s, %s, %s, %s, %s, %s, %s)
			""",(time,hood,clients[hood],status[hood].get("online",0),status[hood].get("offline",0),status[hood].get("unknown",0),status[hood].get("orphaned",0),))
	
	mysql.execute("""
		DELETE FROM stats_hood
		WHERE time < %s
	""",(threshold,))

	mysql.commit()

def router_user_sum(mysql):
	data = mysql.fetchall("""
		SELECT contact, COUNT(id) AS count, SUM(clients) AS clients
		FROM router
		GROUP BY contact
	""")
	result = {}
	for rs in data:
		if rs["contact"]:
			result[rs["contact"]] = {"routers": rs["count"], "clients": rs["clients"]}
	return result
