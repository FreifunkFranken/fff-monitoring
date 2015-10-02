#!/usr/bin/python

from flask import Flask, render_template, request, make_response
from pymongo import MongoClient
from bson.json_util import dumps as bson2json
from bson.objectid import ObjectId
from dateutil import tz

app = Flask(__name__)
client = MongoClient()
db = client.freifunk

tileurls = {
	"links_and_routers": "http://localhost:8000",
	"hoods": "http://localhost:8001",
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

@app.route('/api/get_nearest_router')
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

@app.template_filter('neighbour_color')
def neighbour_color(quality):
	color = "#04ff0a"
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
	return color

@app.template_filter('utc2local')
def utc2local(dt):
	return dt.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
