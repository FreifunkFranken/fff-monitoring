#!/usr/bin/python3

from influxdb import InfluxDBClient
from ffmap.influconfig import infludata
from ffmap.misc import *
import datetime

class FreifunkInflux:

	client = None

	def __init__(self):
		self.client = InfluxDBClient(host=infludata["host"],port=infludata["port"],username=infludata["user"],password=infludata["pw"],database=infludata["db"])
		#self.client.switch_database(infludata["db"])

	def close(self):
		self.client.close()

	def write(self,json,retention):
		self.client.write_points(json,time_precision='s',retention_policy=retention)

	def query(self,sql,params=None):
		if params:
			return self.client.query(sql,bind_params=params,epoch='s')
		else:
			return self.client.query(sql,epoch='s')

	def fetchlist(self,sql,params=None):
		return list(self.query(sql,params).get_points())

	def utcawareint(self,data,keys=None):
		if keys:
			for k in keys:
				data[k] = datetime.datetime.fromtimestamp(data[k],datetime.timezone.utc)
		else:
			data = datetime.datetime.fromtimestamp(data,datetime.timezone.utc)
		return data

	def utctimestamp(self):
		return int(utcnow().timestamp())
