#!/usr/bin/python3

import time
import datetime

from ffmap.config import CONFIG

def utcnow():
	return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

def int2mac(data,keys=None):
	if keys:
		for k in keys:
			data[k] = int2mac(data[k])
		return data
	if data:
		return ':'.join(format(s, '02x') for s in data.to_bytes(6,byteorder='big'))
		#return ':'.join(format(s, '02x') for s in bytes.fromhex('{0:x}'.format(data)))
	else:
		return None

def int2shortmac(data,keys=None):
	if keys:
		for k in keys:
			data[k] = int2shortmac(data[k])
		return data
	if data:
		return format(data, 'x')
	else:
		return None

def shortmac2mac(data):
	if data:
		return ':'.join(format(s, '02x') for s in bytes.fromhex(data.replace(':','')))
	else:
		return None

def mac2int(data):
	return int(data.replace(":",""),16)

def int2mactuple(data,index=None):
	if index:
		for r in data:
			r[index] = int2mac(r[index])
	else:
		for r in data:
			r = int2mac(r)
	return data

def writelog(path, content):
	with open(path, "a") as csv:
		csv.write(time.strftime('{%Y-%m-%d %H:%M:%S}') + " - " + content + "\n")

def writefulllog(content):
	with open(CONFIG["debug_dir"] + "/fulllog.log", "a") as csv:
		csv.write(time.strftime('{%Y-%m-%d %H:%M:%S}') + " - " + content + "\n")

def neighbor_color(quality,netif,rt_protocol):
	color = "#04ff0a"
	if rt_protocol=="BATMAN_V":
		if quality < 10:
			color = "#ff1e1e"
		elif quality < 20:
			color = "#ff4949"
		elif quality < 40:
			color = "#ff6a6a"
		elif quality < 80:
			color = "#ffac53"
		elif quality < 1000:
			color = "#ffeb79"
	else:
		if quality < 105:
			color = "#ff1e1e"
		elif quality < 130:
			color = "#ff4949"
		elif quality < 155:
			color = "#ff6a6a"
		elif quality < 180:
			color = "#ffac53"
		elif quality < 205:
			color = "#ffeb79"
		elif quality < 230:
			color = "#79ff7c"
	if netif.startswith("eth"):
		#color = "#999999"
		color = "#008c00"
	if quality < 0:
		color = "#06a4f4"
	return color

def defrag_table(mysql,table,sleep):
	minustime=0
	allrows=0
	start_time = time.time()

	qry = "ALTER TABLE `%s` ENGINE = InnoDB" % (table)
	mysql.execute(qry)
	mysql.commit()

	end_time = time.time()
	if sleep > 0:
		time.sleep(sleep)

	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "Defragmented table %s: %.3f seconds" % (table,end_time - start_time))
	print("--- Defragmented table %s: %.3f seconds ---" % (table,end_time - start_time))

def defrag_all(mysql,doall=False):
	alltables = ('gw','gw_admin','gw_netif','hoods','netifs','router','router_events','router_gw','router_ipv6','router_neighbor','router_netif','users')
	stattables = ('router_stats','router_stats_gw','router_stats_neighbor','router_stats_netif','stats_global','stats_gw','stats_hood')

	for t in alltables:
		defrag_table(mysql,t,1)

	if doall:
		for t in stattables:
			defrag_table(mysql,t,60)

	writelog(CONFIG["debug_dir"] + "/deletetime.txt", "-------")
