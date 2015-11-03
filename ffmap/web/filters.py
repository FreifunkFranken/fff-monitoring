#!/usr/bin/python3

from flask import Blueprint
from dateutil import tz
from bson.json_util import dumps as bson2json
import datetime
import re

filters = Blueprint("filters", __name__)

@filters.app_template_filter('neighbour_color')
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

@filters.app_template_filter('utc2local')
def utc2local(dt):
	return dt.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())

@filters.app_template_filter('format_dt')
def format_dt(dt):
	return dt.strftime("%Y-%m-%d %H:%M:%S")

@filters.app_template_filter('dt2jstimestamp')
def dt2jstimestamp(dt):
	return int(dt.timestamp())*1000

@filters.app_template_filter('format_dt_ago')
def format_dt_ago(dt):
	diff = datetime.datetime.utcnow() - dt
	s = diff.seconds
	if diff.days > 1:
		return '%i days ago' % diff.days
	elif diff.days == 1:
		return '1 day ago'
	elif s <= 1:
		return 'just now'
	elif s < 60:
		return '%i seconds ago' % s
	elif s < 120:
		return '1 minute ago'
	elif s < 3600:
		return '%i minutes ago' % (s/60)
	elif s < 7200:
		return '1 hour ago'
	else:
		return '%i hours ago' % (s/3600)

@filters.app_template_filter('bson2json')
def bson_to_json(bsn):
	return bson2json(bsn)

@filters.app_template_filter('nbsp')
def nbsp(txt):
	return txt.replace(" ", "&nbsp;")

@filters.app_template_filter('humanize_bytes')
def humanize_bytes(num, suffix='B'):
	for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
		if abs(num) < 1024.0 and unit != '':
			return "%3.1f%s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f%s%s" % (num, 'Yi', suffix)

@filters.app_template_filter('mac2fe80')
def mac_to_ipv6_linklocal(mac):
	# Remove the most common delimiters; dots, dashes, etc.
	mac_bare = re.sub('[%s]+' % re.escape(' .:-'), '', mac)
	mac_value = int(mac_bare, 16)

	# Split out the bytes that slot into the IPv6 address
	# XOR the most significant byte with 0x02, inverting the
	# Universal / Local bit
	high2 = mac_value >> 32 & 0xffff ^ 0x0200
	high1 = mac_value >> 24 & 0xff
	low1 = mac_value >> 16 & 0xff
	low2 = mac_value & 0xffff

	return 'fe80::{:04x}:{:02x}ff:fe{:02x}:{:04x}'.format(high2, high1, low1, low2)

@filters.app_template_filter('status2css')
def status2css(status):
	status_map = {
		"offline": "danger",
		"unknown": "warning",
		"online": "success",
		"reboot": "info",
		"created": "primary",
		"update": "primary",
	}
	return "label label-%s" % status_map.get(status, "default")
