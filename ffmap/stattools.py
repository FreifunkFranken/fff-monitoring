#!/usr/bin/python3

import os
import sys
import datetime
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.dbtools import FreifunkDB

db = FreifunkDB().handle()

def total_clients():
	r = db.routers.aggregate([{"$group": {
		"_id": None,
		"clients": {"$sum": "$system.clients"}
	}}])
	return next(r)["clients"]

def router_status():
	r = db.routers.aggregate([{"$group": {
		"_id": "$status",
		"count": {"$sum": 1}
	}}])
	result = {}
	for rs in r:
		result[rs["_id"]] = rs["count"]
	return result

def router_models():
	r = db.routers.aggregate([{"$group": {
		"_id": "$hardware.name",
		"count": {"$sum": 1}
	}}])
	result = {}
	for rs in r:
		result[rs["_id"]] = rs["count"]
	return result

def router_firmwares():
	r = db.routers.aggregate([{"$group": {
		"_id": "$software.firmware",
		"count": {"$sum": 1}
	}}])
	result = {}
	for rs in r:
		result[rs["_id"]] = rs["count"]
	return result

def hoods():
	r = db.routers.aggregate([{"$group": {
		"_id": {"hood": "$hood", "status": "$status"},
		"count": {"$sum": 1},
	}}])
	result = {}
	for rs in r:
		if not "hood" in rs["_id"]:
			rs["_id"]["hood"] = "default"
		if not rs["_id"]["hood"] in result:
			result[rs["_id"]["hood"]] = {}
		result[rs["_id"]["hood"]][rs["_id"]["status"]] = rs["count"]
	return result

def hoods_sum():
	r = db.routers.aggregate([{"$group": {
		"_id": "$hood",
		"count": {"$sum": 1},
		"clients": {"$sum": "$system.clients"}
	}}])
	result = {}
	for rs in r:
		if not rs["_id"]:
			rs["_id"] = "default"
		result[rs["_id"]] = {"routers": rs["count"], "clients": rs["clients"]}
	return result

def record_global_stats():
	db.stats.insert_one({
		"time": datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc),
		"router_status": router_status(),
		"total_clients": total_clients()
	})


def router_user_sum():
	r = db.routers.aggregate([{"$group": {
		"_id": "$user.nickname",
		"count": {"$sum": 1},
		"clients": {"$sum": "$system.clients"}
	}}])
	result = {}
	for rs in r:
		if rs["_id"]:
			result[rs["_id"]] = {"routers": rs["count"], "clients": rs["clients"]}
	return result
