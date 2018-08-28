#!/usr/bin/python3

from ffmap.routertools import *
from ffmap.gwtools import *
from ffmap.maptools import *
from ffmap.mysqltools import FreifunkMySQL
from ffmap.stattools import record_global_stats, record_hood_stats
from ffmap.config import CONFIG
from ffmap.misc import *

from flask import Blueprint, request, make_response, redirect, url_for, jsonify, Response
from bson.json_util import dumps as bson2json
import json

from operator import itemgetter

import datetime
import time
import traceback

api = Blueprint("api", __name__)

# Load router netif statistics
@api.route('/load_netif_stats/<dbid>')
def load_netif_stats(dbid):
	netif = request.args.get("netif","")
	mysql = FreifunkMySQL()
	netiffetch = mysql.fetchall("""
		SELECT netifs.name AS netif, rx, tx, time
		FROM router_stats_netif
		INNER JOIN netifs ON router_stats_netif.netif = netifs.id
		WHERE router = %s AND netifs.name = %s
	""",(dbid,netif,))
	mysql.close()

	for ns in netiffetch:
		ns["time"] = {"$date": int(mysql.utcawareint(ns["time"]).timestamp()*1000)}

	r = make_response(json.dumps(netiffetch))
	r.mimetype = 'application/json'
	return r

# Load router neighbor statistics
@api.route('/load_neighbor_stats/<dbid>')
def load_neighbor_stats(dbid):
	mysql = FreifunkMySQL()
	neighfetch = mysql.fetchall("""
		SELECT quality, mac, time FROM router_stats_neighbor WHERE router = %s
	""",(dbid,))
	mysql.close()

	neighdata = {}

	for ns in neighfetch:
		ns["time"] = {"$date": int(mysql.utcawareint(ns["time"]).timestamp()*1000)}
		if not ns["mac"] in neighdata:
			neighdata[ns["mac"]] = []
		neighdata[ns["mac"]].append(ns)

	r = make_response(json.dumps(neighdata))
	r.mimetype = 'application/json'
	return r

# map ajax
@api.route('/get_nearest_router')
def get_nearest_router():
	lng = float(request.args.get("lng"))
	lat = float(request.args.get("lat"))
	
	wherelist = []
	if request.args.get("v1") == "on":
		wherelist.append("(v2 = FALSE AND local = FALSE)")
	if request.args.get("v2") == "on":
		wherelist.append("(v2 = TRUE AND local = FALSE)")
	if request.args.get("local") == "on":
		wherelist.append("local = TRUE")
	if wherelist:
		where = " AND ( " + ' OR '.join(wherelist) + " ) "
	else:
		r = make_response(bson2json(None))
		r.mimetype = 'application/json'
		return r
	
	mysql = FreifunkMySQL()
	router = mysql.findone("""
		SELECT r.id, r.hostname, r.lat, r.lng, r.description, r.routing_protocol,
			( acos(  cos( radians(%s) )
						  * cos( radians( r.lat ) )
						  * cos( radians( r.lng ) - radians(%s) )
						  + sin( radians(%s) ) * sin( radians( r.lat ) )
						 )
			) AS distance
		FROM
			router AS r
		WHERE r.lat IS NOT NULL AND r.lng IS NOT NULL """ + where + """ 
		ORDER BY
			distance ASC
		LIMIT 1
	""",(lat,lng,lat,))
	if not router:
		r = make_response(bson2json(None))
		r.mimetype = 'application/json'
		return r
	
	router["neighbours"] = mysql.fetchall("""
		SELECT nb.mac, nb.netif, nb.quality, r.hostname, r.id
		FROM router_neighbor AS nb
		INNER JOIN (
			SELECT router, mac FROM router_netif GROUP BY mac, router
			) AS net ON nb.mac = net.mac
		INNER JOIN router as r ON net.router = r.id
		WHERE nb.router = %s""",(router["id"],))
	mysql.close()
	for n in router["neighbours"]:
		n["color"] = neighbor_color(n["quality"],n["netif"],router["routing_protocol"])
	
	r = make_response(bson2json(router))
	r.mimetype = 'application/json'
	return r

# router by mac (link from router webui)
@api.route('/get_router_by_mac/<mac>')
def get_router_by_mac(mac):
	mysql = FreifunkMySQL()
	res_routers = mysql.fetchall("""
		SELECT id
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		WHERE mac = %s
		GROUP BY mac, id
	""",(mac2int(mac),))
	mysql.close()
	if len(res_routers) != 1:
		return redirect(url_for("router_list", q="mac:%s" % mac))
	else:
		return redirect(url_for("router_info", dbid=res_routers[0]["id"]))

@api.route('/alfred', methods=['GET', 'POST'])
def alfred():
	try:
		start_time = time.time()
		mysql = FreifunkMySQL()
		#set_alfred_data = {65: "hallo", 66: "welt"}
		set_alfred_data = {}
		r = make_response(json.dumps(set_alfred_data))
		#import cProfile, pstats, io
		#pr = cProfile.Profile()
		#pr.enable()
		banned = mysql.fetchall("""
			SELECT mac FROM banned
		""",(),"mac")
		hoodsv2 = mysql.fetchall("""
			SELECT name FROM hoodsv2
		""",(),"name")
		statstime = utcnow()
		netifdict = mysql.fetchdict("SELECT id, name FROM netifs",(),"name","id")
		hoodsdict = mysql.fetchdict("SELECT id, name FROM hoods",(),"name","id")
		if request.method == 'POST':
			try:
				alfred_data = request.get_json()
			except Exception as e:
				writelog(CONFIG["debug_dir"] + "/fail_alfred.txt", "{} - {}".format(request.environ['REMOTE_ADDR'],'JSON parsing failed'))
				writefulllog("Warning: Error converting ALFRED data to JSON:\n__%s" % (request.get_data(True,True).replace("\n", "\n__")))
				return
			
			if alfred_data:
				# load router status xml data
				i = 1
				for mac, xml in alfred_data.get("64", {}).items():
					import_nodewatcher_xml(mysql, mac, xml, banned, hoodsv2, netifdict, hoodsdict, statstime)
					if (i%500 == 0):
						mysql.commit()
					i += 1
				mysql.commit()
				r.headers['X-API-STATUS'] = "ALFRED data imported"
		mysql.close()
		#pr.disable()
		#s = io.StringIO()
		#sortby = 'cumulative'
		#ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
		#ps.print_stats()
		#print(s.getvalue())
		
		writelog(CONFIG["debug_dir"] + "/apitime.txt", "%s - %.3f seconds" % (request.environ['REMOTE_ADDR'],time.time() - start_time))
		
		r.mimetype = 'application/json'
		return r
	except Exception as e:
		writelog(CONFIG["debug_dir"] + "/fail_alfred.txt", "{} - {}".format(request.environ['REMOTE_ADDR'],str(e)))
		writefulllog("Warning: Error while processing ALFRED data: %s\n__%s" % (e, traceback.format_exc().replace("\n", "\n__")))

@api.route('/gwinfo', methods=['GET', 'POST'])
def gwinfo():
	try:
		start_time = time.time()
		mysql = FreifunkMySQL()
		#set_data = {65: "hallo", 66: "welt"}
		set_data = {}
		r = make_response(json.dumps(set_data))
		if request.method == 'POST':
			try:
				gw_data = request.get_json()
			except Exception as e:
				writelog(CONFIG["debug_dir"] + "/fail_gwinfo.txt", "{} - {}".format(request.environ['REMOTE_ADDR'],'JSON parsing failed'))
				writefulllog("Warning: Error converting GWINFO data to JSON:\n__%s" % (request.get_data(True,True).replace("\n", "\n__")))
				return
			
			if gw_data:
				import_gw_data(mysql,gw_data)
				mysql.commit()
				r.headers['X-API-STATUS'] = "GW data imported"
		mysql.close()
		
		writelog(CONFIG["debug_dir"] + "/gwtime.txt", "%s - %.3f seconds" % (request.environ['REMOTE_ADDR'],time.time() - start_time))
		
		r.mimetype = 'application/json'
		return r
	except Exception as e:
		writelog(CONFIG["debug_dir"] + "/fail_gwinfo.txt", "{} - {}".format(request.environ['REMOTE_ADDR'],str(e)))
		writefulllog("Warning: Error while processing GWINFO data: %s\n__%s" % (e, traceback.format_exc().replace("\n", "\n__")))


# https://github.com/ffansbach/de-map/blob/master/schema/nodelist-schema-1.0.0.json
@api.route('/nodelist')
def nodelist():
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT id, hostname, status, clients, last_contact, lat, lng
		FROM router
	""",())
	router_data = mysql.utcawaretuple(router_data,"last_contact")
	mysql.close()
	nodelist_data = {'version': '1.0.0'}
	nodelist_data['nodes'] = list()
	for router in router_data:
		nodelist_data['nodes'].append(
			{
				'id': str(router['id']),
				'name': router['hostname'],
				'node_type': 'AccessPoint',
				'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['id']),
				'status': {
					'online': router['status'] == 'online',
					'clients': router['clients'],
					'lastcontact': router['last_contact'].isoformat()
				}
			}
		)
		if router['lat'] and router['lng']:
			nodelist_data['nodes'][-1]['position'] = {
				'lat': router['lat'],
				'long': router['lng']
			}
	return jsonify(nodelist_data)

@api.route('/wifianal/<selecthood>')
def wifianal(selecthood):
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT hostname, mac, netif
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		INNER JOIN hoods ON router.hood = hoods.id
		WHERE hoods.name = %s
		GROUP BY router.id, netif
	""",(selecthood,))
	mysql.close()
	
	return wifianalhelper(router_data,"Hood: " + selecthood)

@api.route('/wifianalall')
def wifianalall():
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT hostname, mac, netif
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		GROUP BY id, netif
	""",())
	mysql.close()
	
	return wifianalhelper(router_data,"ALL hoods")

def wifianalhelper(router_data, headline):
	s = "#----------WifiAnalyzer alias file----------\n"
	s += "# \n"
	s += "#Freifunk Franken\n"
	s += "#" + headline + "\n"
	s += "# \n"
	s += "#Encoding: UTF-8.\n"
	s += "#The line starts with # is comment.\n"
	s += "# \n"
	s += "#Content line format:\n"
	s += "#bssid1|alias of bssid1\n"
	s += "#bssid2|alias of bssid2\n"
	s += "# \n"
	
	for router in router_data:
		if not router['mac']:
			continue
		if router["netif"] == 'br-mesh':
			s += int2mac(router["mac"]) + "|Mesh_" + router['hostname'] + "\n"
		elif router["netif"] == 'w2ap':
			s += int2mac(router["mac"]) + "|" + router['hostname'] + "\n"
		elif router["netif"] == 'w5ap':
			s += int2mac(router["mac"]) + "|W5_" + router['hostname'] + "\n"
		elif router["netif"] == 'w5mesh':
			s += int2mac(router["mac"]) + "|W5Mesh_" + router['hostname'] + "\n"
	
	return Response(s,mimetype='text/plain')

@api.route('/dnslist')
def dnslist():
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT hostname, mac, MIN(ipv6) AS fd43
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		INNER JOIN router_ipv6 ON router.id = router_ipv6.router AND router_netif.netif = router_ipv6.netif
		WHERE LEFT(HEX(ipv6),4) = 'fd43'
		GROUP BY hostname, mac
	""",())
	mysql.close()

	s = ""
	for router in router_data:
		s += int2shortmac(router["mac"]) + "\t" + bintoipv6(router["fd43"]) + "\n"

	return Response(s,mimetype='text/plain')

@api.route('/dnsentries')
def dnsentries():
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT hostname, mac, MIN(ipv6) AS fd43
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		INNER JOIN router_ipv6 ON router.id = router_ipv6.router AND router_netif.netif = router_ipv6.netif
		WHERE LEFT(HEX(ipv6),4) = 'fd43'
		GROUP BY hostname, mac
	""",())
	mysql.close()

	s = ""
	for router in router_data:
		s += int2shortmac(router["mac"]) + ".fff.community.  300  IN  AAAA  " + bintoipv6(router["fd43"]) + "    ; " + router["hostname"] + "\n"

	return Response(s,mimetype='text/plain')

@api.route('/routers')
def routers():
	# Suppresses routers without br-mesh
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT router.id, hostname, status, hoods.id AS hoodid, hoods.name AS hood, contact, nickname, hardware, firmware, clients, lat, lng, last_contact, mac, sys_loadavg
		FROM router
		INNER JOIN hoods ON router.hood = hoods.id
		INNER JOIN router_netif ON router.id = router_netif.router
		LEFT JOIN users ON router.contact = users.email
		WHERE netif = 'br-mesh'
	""")
	router_data = mysql.utcawaretuple(router_data,"last_contact")
	router_net = mysql.fetchall("""
		SELECT id, netif, COUNT(router) AS count
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		GROUP BY id, netif
	""")
	mysql.close()
	net_dict = {}
	for rs in router_net:
		if not rs["id"] in net_dict:
			net_dict[rs["id"]] = []
		net_dict[rs["id"]].append(rs["netif"])
	nodelist_data = {'version': '1.0.0'}
	nodelist_data['nodes'] = list()
	
	for router in router_data:
		fastd = 0
		l2tp = 0
		
		if router["id"] in net_dict:
			for netif in net_dict[router["id"]]:
				if netif == 'fffVPN':
					fastd += 1
				elif netif.startswith('l2tp'):
					l2tp += 1
				#elif netif['netif'] == 'br-mesh' and 'mac' in netif:
				#	mac = netif["mac"]
		
		if not router['mac']:
			continue
		
		nodelist_data['nodes'].append(
			{
				'id': str(router['id']),
				'name': router['hostname'],
				'mac': int2mac(router['mac']),
				'hoodid': router['hoodid'],
				'hood': router['hood'],
				'status': router['status'],
				'user': router['nickname'],
				'hardware': router['hardware'],
				'firmware': router['firmware'],
				'loadavg': router['sys_loadavg'],
				'href': 'https://monitoring.freifunk-franken.de/mac/' + int2shortmac(router['mac']),
				'clients': router['clients'],
				'lastcontact': router['last_contact'].isoformat(),
				'uplink': {
					'fastd': fastd,
					'l2tp': l2tp
				}
			}
		)
		nodelist_data['nodes'][-1]['position'] = {
			'lat': router['lat'],
			'lng': router['lng']
		}
	return jsonify(nodelist_data)

@api.route('/nopos')
def no_position():
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT router.id, hostname, contact, nickname, firmware
		FROM router
		LEFT JOIN users ON router.contact = users.email
		WHERE lat IS NULL OR lng IS NULL
	""")
	mysql.close()
	#nodelist_data = dict()
	nodelist_data = list()
	for router in router_data:
		nick = router['nickname']
		if not nick:
			nick = ""
		nodelist_data.append(
			{
				'name': router['hostname'],
				'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['id']),
				'firmware': router['firmware'],
				'contact': router['contact'],
				'owner': nick
			}
		)

	nodelist_data2 = sorted(nodelist_data, key=itemgetter('owner'), reverse=False)
	nodes = dict()
	nodes['nodes'] = list(nodelist_data2)

	return jsonify(nodes)

@api.route('/routers_by_nickname/<nickname>')
def get_routers_by_nickname(nickname):
	mysql = FreifunkMySQL()
	users = mysql.fetchall("""
		SELECT id
		FROM users
		WHERE nickname = %s
		LIMIT 1
	""",(nickname,))
	if len(users)==0:
		mysql.close()
		return "User not found"

	nodelist_data = dict()
	nodelist_data['nodes'] = list()
	routers = mysql.fetchall("""
		SELECT router.id, hostname, contact, nickname, firmware, mac, fe80_addr
		FROM router
		INNER JOIN users ON router.contact = users.email
		INNER JOIN router_netif ON router.id = router_netif.router
		WHERE nickname = %s AND netif = 'br-mesh'
		ORDER BY hostname ASC
	""",(nickname,))
	mysql.close()
	for router in routers:
		nodelist_data['nodes'].append(
		{
				'name': router['hostname'],
				'oid': str(router['id']),
				'mac': int2mac(router['mac']),
				'fe80_addr': bintoipv6(router['fe80_addr'])
			}
		)
	return jsonify(nodelist_data)

@api.route('/routers_by_keyxchange_id/<keyxchange_id>')
def get_routers_by_keyxchange_id(keyxchange_id):
	mysql = FreifunkMySQL()
	hood = mysql.findone("""
		SELECT name
		FROM hoodsv1
		WHERE id = %s
		LIMIT 1
	""",(int(keyxchange_id),))
	if not hood:
		mysql.close()
		return "Hood not found"

	nodelist_data = dict()
	nodelist_data['nodes'] = list()
	routers = mysql.fetchall("""
		SELECT router.id, hostname, hardware, mac, fe80_addr, firmware, lat, lng, contact, position_comment, description
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		INNER JOIN hoods ON router.hood = hoods.id
		WHERE hoods.name = %s AND netif = 'br-mesh'
		ORDER BY hostname ASC
	""",(hood["name"],))
	mysql.close()
	for router in routers:
		nodelist_data['nodes'].append(
			{
				'name': router['hostname'],
				'ipv6_fe80_addr': bintoipv6(router['fe80_addr']),
				'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['id']),
				'firmware': router['firmware'],
				'hardware': router['hardware'],
				'contact': router['contact'],
				'description': router['description']
			}
		)
		nodelist_data['nodes'][-1]['position'] = {
			'lat': router['lat'],
			'long': router['lng']
		}
		if router['position_comment']:
			nodelist_data['nodes'][-1]['position']['comment'] = router['position_comment']
	return jsonify(nodelist_data)
