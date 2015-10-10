#!/usr/bin/python3

from pymongo import MongoClient

class FreifunkDB(object):
	client = None
	db = None

	@classmethod
	def handle(cls):
		if not cls.client:
			cls.client = MongoClient()
		if not cls.db:
			cls.db = cls.client.freifunk
		return cls.db
