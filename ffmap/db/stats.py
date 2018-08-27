#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()

mysql.execute("""
	CREATE TABLE `stats_global` (
		`time` int(11) NOT NULL,
		`clients` mediumint(9) NOT NULL,
		`online` smallint(6) NOT NULL,
		`offline` smallint(6) NOT NULL,
		`unknown` smallint(6) NOT NULL,
		`orphaned` smallint(6) NOT NULL,
		`rx` int(10) UNSIGNED DEFAULT NULL,
		`tx` int(10) UNSIGNED DEFAULT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `stats_global`
		ADD PRIMARY KEY (`time`)
""")

mysql.execute("""
	CREATE TABLE stats_gw (
		`time` int(11) NOT NULL,
		`mac` bigint(20) UNSIGNED NOT NULL,
		`clients` mediumint(9) NOT NULL,
		`online` smallint(6) NOT NULL,
		`offline` smallint(6) NOT NULL,
		`unknown` smallint(6) NOT NULL,
		`orphaned` smallint(6) NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE stats_gw
		ADD PRIMARY KEY (`time`,`mac`),
		ADD KEY `mac` (`mac`)
""")

mysql.execute("""
	CREATE TABLE stats_hood (
		`time` int(11) NOT NULL,
		`hood` varchar(30) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
		`clients` mediumint(9) NOT NULL,
		`online` smallint(6) NOT NULL,
		`offline` smallint(6) NOT NULL,
		`unknown` smallint(6) NOT NULL,
		`orphaned` smallint(6) NOT NULL,
		`rx` int(10) UNSIGNED DEFAULT NULL,
		`tx` int(10) UNSIGNED DEFAULT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE stats_hood
		ADD PRIMARY KEY (`time`,`hood`),
		ADD KEY `hood` (`hood`)
""")

mysql.commit()

mysql.close()
