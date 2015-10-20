#!/usr/bin/python3

from flask import Blueprint
from dateutil import tz
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

@filters.app_template_filter('humanize_bytes')
def humanize_bytes(num, suffix='B'):
	for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
		if abs(num) < 1024.0:
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
