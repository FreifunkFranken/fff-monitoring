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
	'nickname',
	'hardware',
	'firmware',
	'mac',
	'hostname',
	'contact',
)

def parse_router_list_search_query(args):
	query_usr = bson.SON()
	if "q" in args:
		for word in args["q"].strip().split(" "):
			if not word:
				# Case of "q=" without arguments
				break
			if not ':' in word:
				key = "hostname"
				value = word
			else:
				key, value = word.split(':', 1)
			if key in allowed_filters:
				query_usr[key] = query_usr.get(key, "") + value
	s = ""
	t = []
	i = 0
	for key, value in query_usr.items():
		if i==0:
			prefix = " WHERE "
		else:
			prefix = " AND "
		if value.startswith('!'):
			no = "NOT "
			value = value[1:]
		else:
			no = ""
		
		if value == "EXISTS":
			k = key + ' <> "" AND ' + key + " IS NOT NULL"
		elif value == "EXISTS_NOT":
			k = key + ' = "" OR ' + key + " IS NULL"
		elif key == 'mac':
			k = no + "mac = %s"
			t.append(value.lower())
		elif (key == 'hostname') or (key == 'hardware') or (key == 'firmware'):
			k = key + " {} REGEXP %s".format(no)
			t.append(value)
		elif key == 'contact':
			k = "contact {} REGEXP %s".format(no)
			t.append(value)
		else:
			k = no + key + " = %s"
			t.append(value)
		i += 1
		s += prefix + k
	return (s, tuple(t), format_query(query_usr))

def send_email(recipient, subject, content, sender="FFF Monitoring <noreply@monitoring.freifunk-franken.de>"):
	msg = MIMEText(content)
	msg['Subject'] = subject
	msg['From'] = sender
	msg['To'] = recipient
	s = smtplib.SMTP('localhost')
	s.send_message(msg)
	s.quit()

def is_authorized(owner, session):
	if ("user" in session) and (owner == session.get("user")):
		return True
	elif session.get("admin"):
		return True
	else:
		return False
