#!/usr/bin/python3

from influxdb import InfluxDBClient
from ffmap.influconfig import infludata, influpolicies
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

def influ_connect(user=None,pw=None):
	if user and pw:
		print('Connect with user ' + user + ' ...')
		client = InfluxDBClient(host=infludata["host"],port=infludata["port"],username=user,password=pw,database=infludata["db"])
	else:
		print('Connect without user ...')
		client = InfluxDBClient(host=infludata["host"],port=infludata["port"],database=infludata["db"])

	return client

def influ_policies():
	return influpolicies

def influ_set_retention(update,policies,user=None,pw=None):
	client = influ_connect(user,pw)

	if update:
		task = 'ALTER'
	else:
		task = 'CREATE'

	for k, v in policies.items():
		client.query('{} RETENTION POLICY {} ON "fff-monitoring" DURATION {}d REPLICATION 1'.format(task,k,v))

	print('Done.')
