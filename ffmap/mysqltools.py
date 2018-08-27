#!/usr/bin/python3

import MySQLdb
from ffmap.mysqlconfig import mysq
from ffmap.misc import *
import datetime

#import pytz

class FreifunkMySQL:
	
	db = None
	cur = None

	def __init__(self):
		#global mysq
		self.db = MySQLdb.connect(host=mysq["host"], user=mysq["user"], passwd=mysq["passwd"], db=mysq["db"], charset="utf8")
		#self.db.set_character_set('utf8')
		self.cur = self.db.cursor(MySQLdb.cursors.DictCursor)

	def close(self):
		self.db.close()

	def cursor(self):
		return self.cur

	def commit(self):
		self.db.commit()
	
	def fetchall(self,str,tup=(),key=None):
		self.cur.execute(str,tup)
		result = self.cur.fetchall()
		if len(result) > 0:
			if key:
				rnew = []
				for r in result:
					rnew.append(r[key])
				return rnew
			else:
				return result
		else:
			return ()
	
	def fetchdict(self,str,tup,key,value=None):
		self.cur.execute(str,tup)
		dict = {}
		for d in self.cur.fetchall():
			if value:
				dict[d[key]] = d[value]
			else:
				dict[d[key]] = d
		return dict
	
	def findone(self,str,tup,sel=None):
		self.cur.execute(str,tup)
		result = self.cur.fetchall()
		if len(result) > 0:
			if sel:
				return result[0][sel]
			else:
				return result[0]
		else:
			return False
	
	def executemany(self,a,b):
		if not b:
			return 0
		return self.cur.executemany(a,b)
	
	def execute(self,a,b=None):
		if b:
			return self.cur.execute(a,b)
		else:
			return self.cur.execute(a)
	
	def utcnow(self):
		return utcnow().strftime('%Y-%m-%d %H:%M:%S')
	
	def utctimestamp(self):
		return int(utcnow().timestamp())
	
	def formatdt(self,dt):
		return dt.strftime('%Y-%m-%d %H:%M:%S')
	
	def formattimestamp(self,t):
		return int(t.timestamp())
	
	def utcawareint(self,data,keys=None):
		if keys:
			for k in keys:
				data[k] = datetime.datetime.fromtimestamp(data[k],datetime.timezone.utc)
		else:
			data = datetime.datetime.fromtimestamp(data,datetime.timezone.utc)
		return data
	
	def utcawaretupleint(self,data,index=None):
		if index:
			for r in data:
				r[index] = datetime.datetime.fromtimestamp(r[index],datetime.timezone.utc)
		else:
			for r in data:
				r = datetime.datetime.fromtimestamp(r,datetime.timezone.utc)
		return data
	
	def utcaware(self,data,keys=None):
		if keys:
			for k in keys:
				#self.utcaware(data[k])
				#data[k] = pytz.utc.localize(data[k])
				data[k] = data[k].replace(tzinfo=datetime.timezone.utc)
		else:
			#data = pytz.utc.localize(data)
			data = data.replace(tzinfo=datetime.timezone.utc)
		return data
	
	def utcawaretuple(self,data,index=None):
		if index:
			for r in data:
				#self.utcaware(r[index])
				#r[index] = pytz.utc.localize(r[index])
				r[index] = r[index].replace(tzinfo=datetime.timezone.utc)
		else:
			for r in data:
				#self.utcaware(r)
				#r = pytz.utc.localize(r)
				r = r.replace(tzinfo=datetime.timezone.utc)
		return data
