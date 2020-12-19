#!/usr/bin/python3

from flask import Blueprint, session
from dateutil import tz
from bson.json_util import dumps as bson2json
import os
import sys
import json
import datetime
import re
import hashlib
from ffmap.misc import int2mac, int2shortmac, inttoipv4, bintoipv6
from ipaddress import ip_address

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))
from ffmap.misc import *

filters = Blueprint("filters", __name__)

@filters.app_template_filter('sumdict')
def sumdict(d):
	return sum(d.values())

@filters.app_template_filter('v2userpercent')
def v2formatpercent(d):
	return "{:.0f}".format(v2numberpercent(d))

def v2numberpercent(d):
	if d.get("v1",0) > 0 or d.get("v2",0) > 0:
		return d["v2"] * 100 / ( d["v1"] + d["v2"] )
	else:
		return 0.0

@filters.app_template_filter('v2colorpercent')
def v2colorpercent(d):
	pc = v2numberpercent(d)
	color = "000000"
	if pc > 99:
		color = "008800"
	elif pc > 75:
		color = "00d93d"
	elif pc > 50:
		color = "ffc926"
	elif pc > 25:
		color = "ff9326"
	elif pc > 1:
		color = "ff0000"
	return "color:#" + color

@filters.app_template_filter('longip')
def longip(d):
	if len(d) > 32:
		return d.replace('::','::... ...::')
	else:
		return d

@filters.app_template_filter('int2mac')
def int2macfilter(d):
	return int2mac(d)

@filters.app_template_filter('int2shortmac')
def int2shortmacfilter(d):
	return int2shortmac(d)

@filters.app_template_filter('int2ipv4')
def int2ipv4filter(d):
	return inttoipv4(d)

@filters.app_template_filter('bin2ipv6')
def bin2ipv6filter(d):
	return bintoipv6(d)

@filters.app_template_filter('ip2int')
def ip2intfilter(d):
	try:
		return int(ip_address(d))
	except ValueError as e:
		return 0

@filters.app_template_filter('ipnet2int')
def ipnet2intfilter(d):
	try:
		return int(ip_address(d.split("/")[0]))
	except ValueError as e:
		return 0

@filters.app_template_filter('utc2local')
def utc2local(dt):
	return dt.astimezone(tz.tzlocal())

@filters.app_template_filter('format_dt')
def format_dt(dt):
	return dt.strftime("%Y-%m-%d %H:%M:%S")

@filters.app_template_filter('format_dt_date')
def format_dt_date(dt):
	return dt.strftime("%Y-%m-%d")

@filters.app_template_filter('dt2jstimestamp')
def dt2jstimestamp(dt):
	return int(dt.timestamp())*1000

@filters.app_template_filter('format_dt_ago')
def format_dt_ago(dt):
	diff = utcnow() - dt
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

@filters.app_template_filter('format_ts_diff')
def format_dt_diff(ts):
	diff = datetime.timedelta(seconds=ts)
	s = diff.seconds
	if diff.days > 1:
		return '%i days' % diff.days
	elif diff.days == 1:
		return '1 day'
	elif s <= 1:
		return '< 1 sec'
	elif s < 60:
		return '%i sec' % s
	elif s < 120:
		return '1 min'
	elif s < 3600:
		return '%i min' % (s/60)
	elif s < 7200:
		return '1 hour'
	else:
		return '%i hours' % (s/3600)

@filters.app_template_filter('bson2json')
def bson_to_json(bsn):
	return bson2json(bsn)

@filters.app_template_filter('statbson2json')
def statbson_to_json(bsn):
	for point in bsn:
		point["time"] = {"$date": int(point["time"].timestamp()*1000)}
	return json.dumps(bsn)

@filters.app_template_filter('shortbson2json')
def shortbson_to_json(bsn):
	for point in bsn:
		point["t"] = {"$date": int(point["t"].timestamp()*1000)}
	return json.dumps(bsn)

@filters.app_template_filter('nbsp')
def nbsp(txt):
	return txt.replace(" ", "&nbsp;")

@filters.app_template_filter('humanize_bytes')
def humanize_bytes(num, suffix='B'):
	for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
		if abs(num) < 1024.0 and unit != '':
			return "%3.1f %s%s" % (num, unit, suffix)
		num /= 1024.0
	return "%.1f %s%s" % (num, 'Yi', suffix)

@filters.app_template_filter('bytes_to_bits')
def bytes_to_bits(num, suffix='b'):
	num *= 8.0
	for unit in ['','k','M','G','T','P','E','Z']:
		if abs(num) < 1000.0 and unit != '':
			return "%3.1f %s%s" % (num, unit, suffix)
		num /= 1000.0
	return "%.1f %s%s" % (num, 'Y', suffix)

@filters.app_template_filter('mac2fe80')
def mac_to_ipv6_linklocal(mac):
	if not mac:
		return ''

	# Remove the most common delimiters; dots, dashes, etc.
	mac_bare = re.sub('[%s]+' % re.escape(' .:-'), '', mac)
	return macint_to_ipv6_linklocal(int(mac_bare, 16))

@filters.app_template_filter('macint2fe80')
def macint_to_ipv6_linklocal(mac_value):
	if not mac_value:
		return ''

	# Split out the bytes that slot into the IPv6 address
	# XOR the most significant byte with 0x02, inverting the
	# Universal / Local bit
	high2 = mac_value >> 32 & 0xffff ^ 0x0200
	high1 = mac_value >> 24 & 0xff
	low1 = mac_value >> 16 & 0xff
	low2 = mac_value & 0xffff

	return 'fe80::{:x}:{:x}ff:fe{:x}:{:x}'.format(high2, high1, low1, low2)

@filters.app_template_filter('status2css')
def status2css(status):
	status_map = {
		"offline": "danger",
		"unknown": "warning",
		"online": "success",
		"reboot": "info",
		"created": "primary",
		"netmon": "primary",
		"update": "primary",
		"orphaned": "default",
		"admin": "warning",
	}
	return "label label-%s" % status_map.get(status, "default")

@filters.app_template_filter('anon_email')
def anon_email(email, replacement_char='.'):
	if 'user' in session:
		return email

	try:
		def anon_str(s, full=False):
			if full:
				return replacement_char * len(s)
			else:
				hide_pos = int(len(s)/2)
				return s[:hide_pos] + replacement_char + s[(hide_pos+1):]
		prefix, tld = email.rsplit('.', 1)
		user, domain = prefix.split('@')
		return '%s@%s.%s' % (anon_str(user), anon_str(domain), anon_str(tld, True))
	except:
		return email

@filters.app_template_filter('anon_email_regex')
def anon_email_regex(email):
	return anon_email(email, '*').replace('.', '\.').replace('*', '.').replace('+', '\+').replace('_', '\_')

@filters.app_template_filter('gravatar_url')
def gravatar_url(email):
	return "https://www.gravatar.com/avatar/%s?d=identicon" % hashlib.md5(email.encode("UTF-8").lower()).hexdigest()

@filters.app_template_filter('webui_addr')
def webui_addr(router_netifs):
	for br_mesh in filter(lambda n: n["netif"] == "br-mesh", router_netifs):
		for ipv6 in br_mesh["ipv6_addrs"]:
			ipv6 = bintoipv6(ipv6)
			if not ipv6:
				return None
			if ipv6.startswith("fd43"):
				# This selects the first ULA address, if present
				return ipv6
			if ipv6.startswith("fdff") and len(ipv6) > 10:
				# This selects the first fdff address, if present (and skips fdff::1)
				return ipv6
	return None

@filters.app_template_filter('format_airtime')
def format_airtime(airtime):
	return "%.0f %%" % (airtime*100)

@filters.app_template_filter('format_query')
def format_query(query):
	return query.replace(" ","_").replace(".","\.").replace("(","\(").replace(")","\)")
