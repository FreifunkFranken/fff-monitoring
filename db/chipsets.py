#!/usr/bin/python

import pymongo
from pymongo import MongoClient
client = MongoClient()

db = client.freifunk

#FIXME: more chipsets
chipsets = {
	"Atheros AR9344 rev 2":           "TL-WDR4300",
	"Atheros AR7240 rev 2":           "TL-WR741NDv2",
	"Atheros AR9330 rev 1":           "TL-WR741NDv4",
	"Atheros AR7241 rev 1":           "TL-WR841NDv7",
	"Atheros AR9341 rev 1":           "TL-WR841NDv8",
	"Atheros AR9341 rev 2":           "TL-WR841NDv8",
	"Atheros AR9341 rev 3":           "TL-WR841NDv8",
	"Qualcomm Atheros QCA9533 rev 1": "TL-WR841NDv9",
	"Atheros AR9132 rev 2":           "TL-WR1043NDv1",
	"Qualcomm Atheros QCA9558 rev 0": "TL-WR1043NDv2",
}

# create index
db.chipsets.create_index("name", unique=True)

for chipset, hardware in chipsets.items():
	try:
		db.chipsets.insert({"name": chipset, "hardware": hardware})
	except pymongo.errors.DuplicateKeyError:
		pass
