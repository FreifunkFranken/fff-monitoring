#!/usr/bin/python3

import datetime

def utcnow():
	return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
