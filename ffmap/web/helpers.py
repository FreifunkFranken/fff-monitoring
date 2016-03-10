#!/usr/bin/python3

import bson
import re
import smtplib
from email.mime.text import MIMEText

def format_query(query_usr):
	query_list = []
	for key, value in query_usr.items():
		if key == "hostname":
			qtag = ""
		else:
			qtag = "%s:" % key
		query_list.append("%s%s" % (qtag, value))
	return " ".join(query_list)

allowed_filters = (
	'status',
	'hood',
	'community',
	'user.nickname',
	'hardware.name',
	'software.firmware',
	'netifs.mac',
	'netifs.name',
	'netmon_id',
	'hostname',
	'system.contact',
)
def parse_router_list_search_query(args):
	query_usr = bson.SON()
	if "q" in args:
		for word in args["q"].strip().split(" "):
			if not ':' in word:
				key = "hostname"
				value = word
			else:
				key, value = word.split(':', 1)
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
		elif key == 'netifs.name':
			query[key] = {"$regex": value.replace('.', '\.'), "$options": 'i'}
		elif key == 'hostname':
			query[key] = {"$regex": value.replace('.', '\.'), "$options": 'i'}
		elif key == 'hardware.name':
			query[key] = {"$regex": value.replace('.', '\.').replace('_', ' '), "$options": 'i'}
		elif key == 'netmon_id':
			query[key] = int(value)
		elif key == 'system.contact':
			if not '\.' in value:
				value = re.escape(value)
			query[key] = {"$regex": value, "$options": 'i'}
		else:
			query[key] = value
	return (query, format_query(query_usr))

def send_email(recipient, subject, content, sender="FFF Monitoring <noreply@monitoring.freifunk-franken.de>"):
	msg = MIMEText(content)
	msg['Subject'] = subject
	msg['From'] = sender
	msg['To'] = recipient
	s = smtplib.SMTP('localhost')
	s.send_message(msg)
	s.quit()

def is_authorized(owner, session):
	if owner == session.get("user"):
		return True
	elif session.get("admin"):
		return True
	else:
		return False
