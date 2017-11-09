#!/usr/bin/python3

from ffmap.routertools import *
from ffmap.maptools import *
from ffmap.mysqltools import FreifunkMySQL
from ffmap.stattools import record_global_stats, record_hood_stats

from flask import Blueprint, request, make_response, redirect, url_for, jsonify, Response
from bson.json_util import dumps as bson2json
import json

from operator import itemgetter

api = Blueprint("api", __name__)

# map ajax
@api.route('/get_nearest_router')
def get_nearest_router():
	lng = float(request.args.get("lng"))
	lat = float(request.args.get("lat"))
	
	mysql = FreifunkMySQL()
	res_router = mysql.findone("""
		SELECT id, hostname, lat, lng, description,
			( acos(  cos( radians(%s) )
						  * cos( radians( lat ) )
						  * cos( radians( lng ) - radians(%s) )
						  + sin( radians(%s) ) * sin( radians( lat ) )
						 )
			) AS distance
		FROM
			router
		WHERE lat IS NOT NULL AND lng IS NOT NULL
		ORDER BY
			distance ASC
		LIMIT 1
	""",(lat,lng,lat,))
	
	res_router["neighbours"] = mysql.fetchall("""
		SELECT nb.mac, nb.quality, nb.net_if, r.hostname, r.id
		FROM router_neighbor AS nb
		INNER JOIN (
			SELECT router, mac FROM router_netif GROUP BY mac, router
			) AS net ON nb.mac = net.mac
		INNER JOIN router as r ON net.router = r.id
		WHERE nb.router = %s""",(res_router["id"],))
	mysql.close()
	
	r = make_response(bson2json(res_router))
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
	""",(mac.lower(),))
	mysql.close()
	if len(res_routers) != 1:
		return redirect(url_for("router_list", q="netifs.mac:%s" % mac))
	else:
		return redirect(url_for("router_info", dbid=res_routers[0]["id"]))

@api.route('/alfred', methods=['GET', 'POST'])
def alfred():
	try:
		mysql = FreifunkMySQL()
		#cur = mysql.cursor()
		#set_alfred_data = {65: "hallo", 66: "welt"}
		set_alfred_data = {}
		r = make_response(json.dumps(set_alfred_data))
		#import cProfile, pstats, io
		#pr = cProfile.Profile()
		#pr.enable()
		if request.method == 'POST':
			alfred_data = request.get_json()
			
			if alfred_data:
				# load router status xml data
				for mac, xml in alfred_data.get("64", {}).items():
					import_nodewatcher_xml(mysql, mac, xml)
					mysql.commit()
				r.headers['X-API-STATUS'] = "ALFRED data imported"
				detect_offline_routers(mysql)
				delete_orphaned_routers(mysql)
				delete_old_stats(mysql)
				record_global_stats(mysql)
				record_hood_stats(mysql)
				update_mapnik_csv(mysql)
			mysql.close()
		#pr.disable()
		#s = io.StringIO()
		#sortby = 'cumulative'
		#ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
		#ps.print_stats()
		#print(s.getvalue())
		r.mimetype = 'application/json'
		return r
	except Exception as e:     # most generic exception you can catch
		logf = open("/data/fff/fail00.txt", "a")
		logf.write("{}\n".format(e))
		logf.close()


# https://github.com/ffansbach/de-map/blob/master/schema/nodelist-schema-1.0.0.json
@api.route('/nodelist')
def nodelist():
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT id, hostname, status, clients, last_contact, lat, lng
		FROM router
	""",())
	mysql.utcawaretuple(router_data,"last_contact")
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
		if 'position' in router:
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
		WHERE hood = %s
		GROUP BY id, netif
	""",(selecthood,))
	mysql.close()
	
	s = "#----------WifiAnalyzer alias file----------\n"
	s += "# \n"
	s += "#Freifunk Franken\n"
	s += "#Hood: " + selecthood + "\n"
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
			s += router["mac"] + "|Mesh_" + router['hostname'] + "\n"
		elif router["netif"] == 'w2ap':
			s += router["mac"] + "|" + router['hostname'] + "\n"
		elif router["netif"] == 'w5ap':
			s += router["mac"] + "|W5_" + router['hostname'] + "\n"
		elif router["netif"] == 'w5mesh':
			s += router["mac"] + "|W5Mesh_" + router['hostname'] + "\n"
	
	return Response(s,mimetype='text/plain')

@api.route('/routers')
def routers():
	# Suppresses routers without br-mesh
	mysql = FreifunkMySQL()
	router_data = mysql.fetchall("""
		SELECT router.id, hostname, status, hood, contact, nickname, hardware, firmware, clients, lat, lng, last_contact, mac
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		LEFT JOIN users ON router.contact = users.email
		WHERE netif = 'br-mesh'
	""")
	mysql.utcawaretuple(router_data,"last_contact")
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
		
		hood = router['hood']
		user = router['nickname']
		firmware = router['firmware']
		mac = router['mac']
		
		if router["id"] in net_dict:
			for netif in net_dict[router["id"]]:
				if netif == 'fffVPN':
					fastd += 1
				elif netif.startswith('l2tp'):
					l2tp += 1
				#elif netif['netif'] == 'br-mesh' and 'mac' in netif:
				#	mac = netif["mac"]
		
		nodelist_data['nodes'].append(
			{
				'id': str(router['id']),
				'name': router['hostname'],
				'mac': mac,
				'hood': hood,
				'status': router['status'],
				'user': user,
				'hardware': router['hardware'],
				'firmware': firmware,
				'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['id']),
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
				'mac': router['mac'],
				'ipv6_fe80_addr': router['fe80_addr']
			}
		)
	return jsonify(nodelist_data)

@api.route('/routers_by_keyxchange_id/<keyxchange_id>')
def get_routers_by_keyxchange_id(keyxchange_id):
	mysql = FreifunkMySQL()
	hood = mysql.findone("""
		SELECT name
		FROM hoods
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
		WHERE hood = %s AND netif = 'br-mesh'
		ORDER BY hostname ASC
	""",(hood["name"],))
	mysql.close()
	for router in routers:
		nodelist_data['nodes'].append(
			{
				'name': router['hostname'],
				'ipv6_fe80_addr': router['fe80_addr'],
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
