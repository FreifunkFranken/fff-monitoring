#!/usr/bin/python3

from ffmap.routertools import *
from ffmap.maptools import *
from ffmap.dbtools import FreifunkDB
from ffmap.stattools import record_global_stats

from flask import Blueprint, request, make_response, redirect, url_for, jsonify, Response
from pymongo import MongoClient
from bson.json_util import dumps as bson2json
import json

from operator import itemgetter

api = Blueprint("api", __name__)

db = FreifunkDB().handle()

# map ajax
@api.route('/get_nearest_router')
def get_nearest_router():
	res_router = db.routers.find_one(
		{"position": {"$near": {"$geometry": {
			"type": "Point",
			"coordinates": [float(request.args.get("lng")), float(request.args.get("lat"))]
		}}}},
		{
			"hostname": 1,
			"neighbours": 1,
			"position": 1,
			"description": 1,
		}
	)
	r = make_response(bson2json(res_router))
	r.mimetype = 'application/json'
	return r

# router by mac (link from router webui)
@api.route('/get_router_by_mac/<mac>')
def get_router_by_mac(mac):
	res_routers = db.routers.find({"netifs.mac": mac.lower()}, {"_id": 1})
	if res_routers.count() != 1:
		return redirect(url_for("router_list", q="netifs.mac:%s" % mac))
	else:
		return redirect(url_for("router_info", dbid=next(res_routers)["_id"]))

@api.route('/alfred', methods=['GET', 'POST'])
def alfred():
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
				import_nodewatcher_xml(mac, xml)
			r.headers['X-API-STATUS'] = "ALFRED data imported"
		detect_offline_routers()
		delete_orphaned_routers()
		record_global_stats()
		update_mapnik_csv()
	#pr.disable()
	#s = io.StringIO()
	#sortby = 'cumulative'
	#ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
	#ps.print_stats()
	#print(s.getvalue())
	r.mimetype = 'application/json'
	return r


# https://github.com/ffansbach/de-map/blob/master/schema/nodelist-schema-1.0.0.json
@api.route('/nodelist')
def nodelist():
	router_data = db.routers.find(projection=['_id', 'hostname', 'status', 'system.clients', 'position.coordinates', 'last_contact'])
	nodelist_data = {'version': '1.0.0'}
	nodelist_data['nodes'] = list()
	for router in router_data:
		nodelist_data['nodes'].append(
			{
				'id': str(router['_id']),
				'name': router['hostname'],
				'node_type': 'AccessPoint',
				'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['_id']),
				'status': {
					'online': router['status'] == 'online',
					'clients': router['system']['clients'],
					'lastcontact': router['last_contact'].isoformat()
				}
			}
		)
		if 'position' in router:
			nodelist_data['nodes'][-1]['position'] = {
				'lat': router['position']['coordinates'][1],
				'long': router['position']['coordinates'][0]
			}
	return jsonify(nodelist_data)

@api.route('/wifianal/<selecthood>')
def wifianal(selecthood):
	router_data = db.routers.find({'hood': selecthood}, projection=['hostname','netifs'])
	
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
		if not 'netifs' in router:
			continue
		for netif in router['netifs']:
			if not 'mac' in netif:
				continue
			if netif['name'] == 'br-mesh':
				s += netif["mac"] + "|Mesh_" + router['hostname'] + "\n"
			elif netif['name'] == 'w2ap':
				s += netif["mac"] + "|" + router['hostname'] + "\n"
			elif netif['name'] == 'w5ap':
				s += netif["mac"] + "|W5_" + router['hostname'] + "\n"
			elif netif['name'] == 'w5mesh':
				s += netif["mac"] + "|W5Mesh_" + router['hostname'] + "\n"
	
	return Response(s,mimetype='text/plain')

@api.route('/routers')
def routers():
	router_data = db.routers.find(projection=['_id', 'hostname', 'status', 'hood', 'user.nickname', 'hardware.name', 'software.firmware', 'system.clients', 'position.coordinates', 'last_contact', 'netifs'])
	nodelist_data = {'version': '1.0.0'}
	nodelist_data['nodes'] = list()
	
	for router in router_data:
		hood = ""
		user = ""
		firmware = ""
		mac = ""
		fastd = 0
		l2tp = 0
		
		if 'hood' in router:
			hood = router['hood']
		if 'user' in router:
			user = router['user']['nickname']
		if 'software' in router:
			firmware = router['software']['firmware']
		
		if 'netifs' in router:
			for netif in router['netifs']:
				if netif['name'] == 'fffVPN':
					fastd += 1
				elif netif['name'].startswith('l2tp'):
					l2tp += 1
				elif netif['name'] == 'br-mesh' and 'mac' in netif:
					mac = netif["mac"]
		
		nodelist_data['nodes'].append(
			{
				'id': str(router['_id']),
				'name': router['hostname'],
				'mac': mac,
				'hood': hood,
				'status': router['status'],
				'user': user,
				'hardware': router['hardware']['name'],
				'firmware': firmware,
				'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['_id']),
				'clients': router['system']['clients'],
				'lastcontact': router['last_contact'].isoformat(),
				'uplink': {
					'fastd': fastd,
					'l2tp': l2tp
				}
			}
		)
		if 'position' in router:
			nodelist_data['nodes'][-1]['position'] = {
				'lat': router['position']['coordinates'][1],
				'lng': router['position']['coordinates'][0]
			}
	return jsonify(nodelist_data)

@api.route('/nopos')
def no_position():
    router_data = db.routers.find(filter={'position': { '$exists': False}}, projection=['_id', 'hostname', 'system.contact', 'user.nickname', 'software.firmware'])
    #nodelist_data = dict()
    nodelist_data = list()
    for router in router_data:
        nodelist_data.append(
            {
                'name': router['hostname'],
                'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['_id']),
                'firmware': router['software']['firmware']
            }
        )
        if 'system' in router and 'contact' in router['system']:
            nodelist_data[-1]['contact'] = router['system']['contact']
        if 'user' in router and 'nickname' in router['user']:
            nodelist_data[-1]['owner'] = router['user']['nickname']
        else:
            nodelist_data[-1]['owner'] = ''


    nodelist_data2 = sorted(nodelist_data, key=itemgetter('owner'), reverse=False)
    nodes = dict()
    nodes['nodes'] = list(nodelist_data2)

    return jsonify(nodes)

import pymongo
@api.route('/routers_by_nickname/<nickname>')
def get_routers_by_nickname(nickname):
    try:
        user = db.users.find_one({"nickname": nickname})
        assert user
    except AssertionError:
        return "User not found"

    nodelist_data = dict()
    nodelist_data['nodes'] = list()
    routers=db.routers.find({"user._id": user["_id"]}, {"hostname": 1, "netifs": 1, "_id": 1}).sort("hostname", pymongo.ASCENDING)
    for router in routers:
        #print(router['hostname'])
        for netif in router['netifs']:
            if netif['name'] == 'br-mesh':
                #print(netif['ipv6_fe80_addr'])
                nodelist_data['nodes'].append(
                {
                        'name': router['hostname'],
                        'oid': str(router['_id']),
                        'ipv6_fe80_addr': netif['ipv6_fe80_addr']
                    }
                )
    return jsonify(nodelist_data)


@api.route('/routers_by_keyxchange_id/<keyxchange_id>')
def get_routers_by_keyxchange_id(keyxchange_id):
    try:
        hood = db.hoods.find_one({"keyxchange_id": int(keyxchange_id)})
        assert hood
    except AssertionError:
        return "Hood not found"
    nodelist_data = dict()
    nodelist_data['nodes'] = list()
    routers = db.routers.find({"hood": hood["name"]}, {"hostname": 1, "hardware": 1, "netifs": 1, "_id": 1, "software": 1, "position": 1, "system": 1, "position_comment": 1, "description": 1}).sort("hostname", pymongo.ASCENDING)
    for router in routers:
        for netif in router['netifs']:
            if netif['name'] == 'br-mesh':
                if 'ipv6_fe80_addr' not in netif:
                    continue
                nodelist_data['nodes'].append(
                    {
                        'name': router['hostname'],
                        'ipv6_fe80_addr': netif['ipv6_fe80_addr'],
                        'href': 'https://monitoring.freifunk-franken.de/routers/' + str(router['_id']),
                        'firmware': router['software']['firmware'],
                        'hardware': router['hardware']['name']
                    }
                )
                if 'position' in router:
                    nodelist_data['nodes'][-1]['position'] = {
                        'lat': router['position']['coordinates'][1],
                        'long': router['position']['coordinates'][0]
                    }
                if 'system' in router and 'contact' in router['system']:
                    nodelist_data['nodes'][-1]['contact'] = router['system']['contact']
                if 'description' in router:
                    nodelist_data['nodes'][-1]['description'] = router['description']

                if 'position_comment' in router:
                    nodelist_data['nodes'][-1]['position']['comment'] = router['position_comment']
    return jsonify(nodelist_data)
