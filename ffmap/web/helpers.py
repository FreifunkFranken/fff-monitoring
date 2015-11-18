#!/usr/bin/python3

import bson

def format_query(query_usr):
	query_list = []
	for key, value in query_usr.items():
		if key == "hostname":
			qtag = ""
		else:
			qtag = "%s:" % key
		query_list.append("%s%s" % (qtag, value))
	return " ".join(query_list)

allowed_filters = ('status', 'hood', 'user.nickname', 'hardware.name', 'software.firmware', 'netifs.mac', 'hostname')
def parse_router_list_search_query(args):
	query_usr = bson.SON()
	if "q" in args:
		for word in args["q"].strip().split(" "):
			if not ':' in word:
				key = "hostname"
				value = word
			else:
				key, value = word.split(':')
			if key in allowed_filters:
				query_usr[key] = query_usr.get(key, "") + value
	query = {}
	for key, value in query_usr.items():
		if value == "EXISTS":
			query[key] = {"$exists": True}
		elif value == "EXISTS_NOT":
			query[key] = {"$exists": False}
		elif key == 'netifs.mac':
			query[key] = value.lower()
		elif key == 'hostname':
			query[key] = {"$regex": value, "$options": 'i'}
		else:
			query[key] = value
	return (query, format_query(query_usr))
