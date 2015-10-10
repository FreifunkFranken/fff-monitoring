#!/usr/bin/python3

from flask import Blueprint
from dateutil import tz

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
