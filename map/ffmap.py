#!/usr/bin/python

from flask import Flask, render_template, request, make_response
from pymongo import MongoClient
from bson.json_util import dumps as bson2json

app = Flask(__name__)
client = MongoClient()
db = client.freifunk

tileurls = {
	"links_and_routers": "http://home.heidler.eu:8000",
	"hoods": "http://home.heidler.eu:8001",
}

@app.route('/')
def index():
	return render_template("map.html", tileurls=tileurls)

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

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=False)
