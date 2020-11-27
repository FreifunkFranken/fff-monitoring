#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.influxtools import influ_connect
from influxdb import InfluxDBClient
from getpass import getpass

if len(sys.argv) > 1:
	# read password for user input
	pw = getpass()
	client = influ_connect(sys.argv[1],pw)
else:
	print('Connect without user ...')
	client = influ_connect()

result = client.query("SHOW RETENTION POLICIES")

print('\n{: <18} {: <12} {: <12}'.format("Name","Duration","Shards"))

for p in list(result.get_points()):
	print('{: <18} {: <12} {: <12} {}'.format(p["name"],p["duration"].replace('h0m0s','h'),p["shardGroupDuration"].replace('h0m0s','h'),"default" if p["default"] else ""))
