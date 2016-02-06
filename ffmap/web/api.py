#!/usr/bin/python3

from ffmap.routertools import *
from ffmap.maptools import *
from ffmap.dbtools import FreifunkDB
from ffmap.stattools import record_global_stats

from flask import Blueprint, request, make_response, redirect, url_for
from pymongo import MongoClient
from bson.json_util import dumps as bson2json
import json

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
	if request.method == 'POST':
		alfred_data = request.get_json()
		if alfred_data:
			# load router status xml data
			for mac, xml in alfred_data.get("64", {}).items():
				import_nodewatcher_xml(mac, xml)
			r.headers['X-API-STATUS'] = "ALFRED data imported"
		detect_offline_routers()
		record_global_stats()
		update_mapnik_csv()
	r.mimetype = 'application/json'
	return r
