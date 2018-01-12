#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL
from ffmap.misc import *
from ffmap.config import CONFIG
from flask import request, url_for

import datetime
import time

def import_gw_data(mysql, gw_data):
	if "hostname" in gw_data and "netifs" in gw_data:
		time = utcnow().strftime('%Y-%m-%d %H:%M:%S')
		stats_page = gw_data.get("stats_page","")
		if not stats_page:
			stats_page = None
		mysql.execute("""
			INSERT INTO gw (name, stats_page, last_contact)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE
				stats_page=VALUES(stats_page),
				last_contact=VALUES(last_contact)
		""",(gw_data["hostname"],gw_data["stats_page"],time,))
		
		newid = mysql.findone("SELECT id FROM gw WHERE name = %s LIMIT 1",(gw_data["hostname"],),"id")
		
		ndata = []
		for n in gw_data["netifs"]:
			ndata.append((newid,n["mac"],n["netif"],))
		
		mysql.executemany("""
			INSERT INTO gw_netif (gw, mac, netif)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE
				gw=VALUES(gw),
				netif=VALUES(netif)
		""",ndata)
		
		adata = []
		aid = 0
		for a in gw_data["admins"]:
			aid += 1
			adata.append((newid,a,aid,))
		
		mysql.execute("DELETE FROM gw_admin WHERE gw = %s",(newid,))
		mysql.executemany("""
			INSERT INTO gw_admin (gw, name, prio)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE
				prio=VALUES(prio)
		""",adata)
	else:
		writelog(CONFIG["debug_dir"] + "/fail_gwinfo.txt", "{} - Corrupted file.".format(request.environ['REMOTE_ADDR']))

def gw_name(gw):
	if gw["gw"] and gw["gwif"]:
		s = gw["gw"] + " (" + gw["gwif"] + ")"
	else:
		s = gw["mac"]
	return s
