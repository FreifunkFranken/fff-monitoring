#!/usr/bin/python3

import time
import datetime

from ffmap.config import CONFIG

def utcnow():
	return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

def writelog(path, content):
	with open(path, "a") as csv:
		csv.write(time.strftime('{%Y-%m-%d %H:%M:%S}') + " - " + content + "\n")

def writefulllog(content):
	with open(CONFIG["debug_dir"] + "/fulllog.log", "a") as csv:
		csv.write(time.strftime('{%Y-%m-%d %H:%M:%S}') + " - " + content + "\n")
