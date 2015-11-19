#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.web.api import api
from ffmap.web.filters import filters
from ffmap.dbtools import FreifunkDB
from ffmap import stattools
from ffmap.web.helpers import *

from flask import Flask, render_template, request, Response, redirect, url_for, flash
import bson
import pymongo
from bson.json_util import dumps as bson2json
from bson.objectid import ObjectId

app = Flask(__name__)
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(filters)

db = FreifunkDB().handle()

tileurls = {
	"links_and_routers": "/tiles/links_and_routers",
	"hoods": "/tiles/hoods",
}

@app.route('/')
def index():
	return render_template("index.html")

@app.route('/map')
def router_map():
	return render_template("map.html", tileurls=tileurls)

@app.route('/routers')
def router_list():
	query, query_str = parse_router_list_search_query(request.args)
	return render_template("router_list.html", query_str=query_str, routers=db.routers.find(query, {
		"hostname": 1,
		"status": 1,
		"hood": 1,
		"user.nickname": 1,
		"hardware.name": 1,
		"created": 1,
		"system.uptime": 1,
		"system.clients": 1,
	}).sort("hostname", pymongo.ASCENDING))

@app.route('/routers/<dbid>', methods=['GET', 'POST'])
def router_info(dbid):
	try:
		if request.method == 'POST':
			if request.form.get("act") == "netmon_resync":
				r = db.routers.update_one({"_id": ObjectId(dbid)}, {"$unset": {"netmon_id": 1}})
				assert r.matched_count > 0
				flash("<b>Netmon Sync triggered!</b>", "success")
				return redirect(url_for("router_info", dbid=dbid))
		router = db.routers.find_one({"_id": ObjectId(dbid)})
		assert router
	except (bson.errors.InvalidId, AssertionError):
		return "Router not found"
	if request.args.get('json', None) != None:
		del router["stats"]
		return Response(bson2json(router, sort_keys=True, indent=4), mimetype='application/json')
	else:
		return render_template("router.html", router=router, tileurls=tileurls)

@app.route('/statistics')
def global_statistics():
	hoods = stattools.hoods()
	return render_template("statistics.html",
		stats = db.stats.find({}, {"_id": 0}),
		clients = stattools.total_clients(),
		router_status = stattools.router_status(),
		router_models = stattools.router_models(),
		router_firmwares = stattools.router_firmwares(),
		hoods = hoods,
		hoods_sum = stattools.hoods_sum(),
		newest_routers = db.routers.find({}, {"hostname": 1, "hood": 1, "created": 1}).sort("created", pymongo.DESCENDING).limit(len(hoods)+1)
	)


app.secret_key = os.urandom(24)

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
else:
	app.template_folder = "/usr/share/ffmap/templates"
	app.static_folder = "/usr/share/ffmap/static"
	#app.debug = True
