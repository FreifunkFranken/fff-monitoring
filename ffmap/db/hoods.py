#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()

mysql.execute("""
	CREATE TABLE hoods (
		`id` int(11) NOT NULL,
		`name` varchar(50) COLLATE utf8_unicode_ci NOT NULL,
		`net` varchar(30) COLLATE utf8_unicode_ci NOT NULL,
		`lat` double DEFAULT NULL,
		`lng` double DEFAULT NULL,
		`cos_lat` double DEFAULT NULL,
		`sin_lat` double DEFAULT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE hoods
		ADD PRIMARY KEY (`id`),
		ADD KEY `name` (`name`),
		ADD KEY `lat` (`lat`),
		ADD KEY `lng` (`lng`),
		ADD KEY `cos_lat` (`cos_lat`),
		ADD KEY `sin_lat` (`sin_lat`)
""")

mysql.close()
