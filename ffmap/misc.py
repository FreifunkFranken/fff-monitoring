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

def neighbor_color(quality,rt_protocol):
	if rt_protocol=="BATMAN_V":
		color = "#04ff0a"
		if quality < 0:
			color = "#06a4f4"
		elif quality < 10:
			color = "#ff1e1e"
		elif quality < 20:
			color = "#ff4949"
		elif quality < 40:
			color = "#ff6a6a"
		elif quality < 80:
			color = "#ffac53"
		elif quality < 1000:
			color = "#ffeb79"
	else:
		color = "#04ff0a"
		if quality < 0:
			color = "#06a4f4"
		elif quality < 105:
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
