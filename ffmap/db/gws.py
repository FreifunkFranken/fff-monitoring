#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()

mysql.execute("""
	CREATE TABLE `gw` (
		`id` smallint(5) UNSIGNED NOT NULL,
		`name` varchar(50) COLLATE utf8_unicode_ci NOT NULL,
		`stats_page` varchar(200) COLLATE utf8_unicode_ci DEFAULT NULL,
		`last_contact` datetime NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `gw`
		ADD PRIMARY KEY (`id`),
		ADD UNIQUE KEY `name` (`name`)
""")

mysql.execute("""
	ALTER TABLE `gw`
		MODIFY `id` smallint(5) UNSIGNED NOT NULL AUTO_INCREMENT
""")

mysql.execute("""
	CREATE TABLE `gw_admin` (
		`gw` smallint(5) UNSIGNED NOT NULL,
		`name` varchar(100) COLLATE utf8_unicode_ci NOT NULL,
		`prio` tinyint(3) UNSIGNED NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `gw_admin`
		ADD PRIMARY KEY (`gw`,`name`)
""")

mysql.execute("""
	CREATE TABLE `gw_netif` (
		`gw` smallint(5) UNSIGNED NOT NULL,
		`mac` bigint(20) UNSIGNED NOT NULL,
		`netif` varchar(15) COLLATE utf8_unicode_ci NOT NULL,
		`vpnmac` bigint(20) UNSIGNED DEFAULT NULL,
		`ipv4` char(18) COLLATE utf8_unicode_ci DEFAULT NULL,
		`ipv6` varchar(60) COLLATE utf8_unicode_ci DEFAULT NULL,
		`dhcpstart` char(15) COLLATE utf8_unicode_ci DEFAULT NULL,
		`dhcpend` char(15) COLLATE utf8_unicode_ci DEFAULT NULL,
		`last_contact` datetime NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `gw_netif`
		ADD PRIMARY KEY (`mac`),
		ADD KEY `gw` (`gw`)
""")

mysql.commit()

mysql.close()
