#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()

mysql.execute("""
	CREATE TABLE `stats_global` (
		`time` int(11) NOT NULL,
		`clients` int(11) NOT NULL,
		`online` int(11) NOT NULL,
		`offline` int(11) NOT NULL,
		`unknown` int(11) NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `stats_global`
		ADD PRIMARY KEY (`time`)
""")

mysql.execute("""
	CREATE TABLE stats_hood (
		`hood` varchar(50) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
		`time` int(11) NOT NULL,
		`clients` int(11) NOT NULL,
		`online` int(11) NOT NULL,
		`offline` int(11) NOT NULL,
		`unknown` int(11) NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE stats_hood
		ADD PRIMARY KEY (`time`,`hood`)
""")

mysql.close()
