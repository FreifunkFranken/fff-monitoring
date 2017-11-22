#!/usr/bin/python3

import time
import datetime

def utcnow():
	return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

def writelog(path, content):
	with open(path, "a") as csv:
		csv.write(time.strftime('{%Y-%m-%d %H:%M:%S}') + " - " + content + "\n")
