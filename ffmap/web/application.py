#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.web.api import api
from ffmap.web.filters import filters
from ffmap.dbtools import FreifunkDB

from flask import Flask, render_template, request, make_response
from bson.json_util import dumps as bson2json
from bson.objectid import ObjectId
import json

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
	return render_template("router_list.html", routers=db.routers.find({}, {
		"hostname": 1,
		"status": 1,
		"hood": 1,
		"user.nickname": 1,
		"hardware.name": 1,
	}))

@app.route('/routers/<dbid>')
def router_info(dbid):
	return render_template("router.html", router=db.routers.find_one({"_id": ObjectId(dbid)}), tileurls=tileurls)


if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
else:
	app.template_folder = "/usr/share/ffmap/templates"
	app.static_folder = "/usr/share/ffmap/static"
	#app.debug = True
