#!/usr/bin/python

import nodewatcher

from flask import Blueprint, request, make_response
from pymongo import MongoClient
from bson.json_util import dumps as bson2json
import json

api = Blueprint("api", __name__)

client = MongoClient()
db = client.freifunk

@api.route('/get_nearest_router')
def get_nearest_router():
	res_router = db.routers.find_one({"position": {"$near": {
		"$geometry": {
			"type": "Point",
			"coordinates": [float(request.args.get("lng")), float(request.args.get("lat"))]
		},
	}}})
	r = make_response(bson2json(res_router))
	r.mimetype = 'application/json'
	return r

@api.route('/alfred', methods=['GET', 'POST'])
def alfred():
	#set_alfred_data = {65: "hallo", 66: "welt"}
	set_alfred_data = {}
	r = make_response(json.dumps(set_alfred_data))
	if request.method == 'POST':
		alfred_data = request.get_json()
		# load router status xml data
		for mac, xml in alfred_data.get("64", {}).items():
			nodewatcher.process_router_xml(mac, xml)
		r.headers['X-API-STATUS'] = "ALFRED data imported"
	r.mimetype = 'application/json'
	return r
