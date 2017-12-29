#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()

mysql.execute("""
	CREATE TABLE banned (
		`mac` char(17) COLLATE utf8_unicode_ci NOT NULL,
		`added` datetime NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `banned`
		ADD PRIMARY KEY (`mac`)
""")

mysql.execute("""
	CREATE TABLE netifs (
		`id` smallint(6) UNSIGNED NOT NULL,
		`name` varchar(15) COLLATE utf8_unicode_ci NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE netifs
		ADD PRIMARY KEY (`id`),
		ADD UNIQUE KEY `name` (`name`)
""")

mysql.execute("""
	ALTER TABLE netifs
		MODIFY `id` smallint(6) UNSIGNED NOT NULL AUTO_INCREMENT
""")

mysql.execute("""
	CREATE TABLE router (
		`id` mediumint(8) UNSIGNED NOT NULL,
		`status` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
		`hostname` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`created` datetime NOT NULL,
		`last_contact` datetime NOT NULL,
		`sys_time` datetime NOT NULL,
		`sys_uptime` int(11) NOT NULL,
		`sys_memfree` int(11) NOT NULL,
		`sys_membuff` int(11) NOT NULL,
		`sys_memcache` int(11) NOT NULL,
		`sys_loadavg` float NOT NULL,
		`sys_procrun` smallint(6) NOT NULL,
		`sys_proctot` smallint(6) NOT NULL,
		`clients` smallint(6) NOT NULL,
		`wan_uplink` tinyint(1) NOT NULL,
		`cpu` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`chipset` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`hardware` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`os` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`batman` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`kernel` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`nodewatcher` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`firmware` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`firmware_rev` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`description` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`position_comment` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`community` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`hood` varchar(30) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
		`status_text` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`contact` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`lng` double DEFAULT NULL,
		`lat` double DEFAULT NULL,
		`reset` tinyint(1) NOT NULL DEFAULT '0',
		`neighbors` smallint(6) NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router
		ADD PRIMARY KEY (`id`),
		ADD KEY `created` (`created`),
		ADD KEY `hostname` (`hostname`),
		ADD KEY `status` (`status`),
		ADD KEY `last_contact` (`last_contact`),
		ADD KEY `lat` (`lat`),
		ADD KEY `lng` (`lng`),
		ADD KEY `contact` (`contact`),
		ADD KEY `hood` (`hood`)
""")

mysql.execute("""
	ALTER TABLE router
		MODIFY `id` mediumint(8) UNSIGNED NOT NULL AUTO_INCREMENT
""")

mysql.execute("""
	CREATE TABLE router_events (
		`router` mediumint(8) UNSIGNED NOT NULL,
		`time` datetime NOT NULL,
		`type` varchar(100) COLLATE utf8_unicode_ci NOT NULL,
		`comment` varchar(200) COLLATE utf8_unicode_ci NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router_events
		ADD PRIMARY KEY (`router`,`time`,`type`)
""")

mysql.execute("""
	CREATE TABLE router_ipv6 (
		`router` mediumint(8) UNSIGNED NOT NULL,
		`netif` varchar(15) COLLATE utf8_unicode_ci NOT NULL,
		`ipv6` varchar(60) COLLATE utf8_unicode_ci NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router_ipv6
		ADD PRIMARY KEY (`router`,`netif`,`ipv6`)
""")

mysql.execute("""
	CREATE TABLE router_neighbor (
		`router` mediumint(8) UNSIGNED NOT NULL,
		`mac` char(17) COLLATE utf8_unicode_ci NOT NULL,
		`quality` smallint(6) NOT NULL,
		`net_if` varchar(15) COLLATE utf8_unicode_ci NOT NULL,
		`type` varchar(10) COLLATE utf8_unicode_ci DEFAULT 'l2'
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router_neighbor
		ADD PRIMARY KEY (`router`,`mac`)
""")

mysql.execute("""
	CREATE TABLE router_netif (
		`router` mediumint(8) UNSIGNED NOT NULL,
		`netif` varchar(15) COLLATE utf8_unicode_ci NOT NULL,
		`mtu` smallint(6) NOT NULL,
		`rx_bytes` bigint(20) UNSIGNED NOT NULL,
		`tx_bytes` bigint(20) UNSIGNED NOT NULL,
		`rx` bigint(20) NOT NULL,
		`tx` bigint(20) NOT NULL,
		`fe80_addr` varchar(60) COLLATE utf8_unicode_ci NOT NULL,
		`ipv4_addr` varchar(20) COLLATE utf8_unicode_ci NOT NULL,
		`mac` char(17) COLLATE utf8_unicode_ci NOT NULL,
		`wlan_channel` tinyint(3) UNSIGNED DEFAULT NULL,
		`wlan_type` varchar(10) COLLATE utf8_unicode_ci DEFAULT NULL,
		`wlan_width` tinyint(3) UNSIGNED DEFAULT NULL,
		`wlan_ssid` varchar(32) COLLATE utf8_unicode_ci DEFAULT NULL,
		`wlan_txpower` varchar(8) COLLATE utf8_unicode_ci DEFAULT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router_netif
		ADD PRIMARY KEY (`router`,`netif`),
		ADD KEY `mac` (`mac`)
""")

mysql.execute("""
	CREATE TABLE router_stats (
		`time` int(11) NOT NULL,
		`router` mediumint(8) UNSIGNED NOT NULL,
		`sys_proctot` smallint(6) NOT NULL,
		`sys_procrun` smallint(6) NOT NULL,
		`sys_memcache` int(11) NOT NULL,
		`sys_membuff` int(11) NOT NULL,
		`sys_memfree` int(11) NOT NULL,
		`loadavg` float NOT NULL,
		`clients` smallint(6) NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router_stats
		ADD PRIMARY KEY (`time`,`router`),
		ADD KEY `router` (`router`)
""")

mysql.execute("""
	CREATE TABLE router_stats_neighbor (
		`time` int(11) NOT NULL,
		`router` mediumint(8) UNSIGNED NOT NULL,
		`mac` char(17) COLLATE utf8_unicode_ci NOT NULL,
		`quality` smallint(6) NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router_stats_neighbor
		ADD PRIMARY KEY (`time`,`router`,`mac`),
		ADD KEY `router` (`router`)
""")

mysql.execute("""
	CREATE TABLE router_stats_netif (
		`time` int(11) NOT NULL,
		`router` mediumint(8) UNSIGNED NOT NULL,
		`netif` smallint(6) UNSIGNED NOT NULL,
		`rx` int(10) UNSIGNED NOT NULL,
		`tx` int(10) UNSIGNED NOT NULL,
		`deletebit` tinyint(1) NOT NULL DEFAULT '0'
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE router_stats_netif
		ADD PRIMARY KEY (`time`,`router`,`netif`),
		ADD KEY `router` (`router`),
		ADD KEY `deletebit` (`deletebit`)
""")

mysql.close()
