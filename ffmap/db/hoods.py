#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()

mysql.execute("""
	CREATE TABLE `hoods` (
		`id` smallint(6) UNSIGNED NOT NULL,
		`name` varchar(30) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `hoods`
		ADD PRIMARY KEY (`id`),
		ADD UNIQUE KEY `name` (`name`)
""")

mysql.execute("""
	ALTER TABLE `hoods`
		MODIFY `id` smallint(6) UNSIGNED NOT NULL AUTO_INCREMENT
""")

mysql.execute("""
	ALTER TABLE hoods AUTO_INCREMENT = 30001
""")

mysql.execute("""
	INSERT INTO hoods (id, name)
	VALUES (%s, %s)
""",(10000,NoCoordinates,))

mysql.execute("""
	CREATE TABLE `hoodsv1` (
		`id` int(10) UNSIGNED NOT NULL,
		`name` varchar(30) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
		`net` varchar(30) COLLATE utf8_unicode_ci NOT NULL,
		`lat` double DEFAULT NULL,
		`lng` double DEFAULT NULL,
		`cos_lat` double DEFAULT NULL,
		`sin_lat` double DEFAULT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `hoodsv1`
		ADD PRIMARY KEY (`id`),
		ADD UNIQUE KEY `name` (`name`),
		ADD KEY `lat` (`lat`),
		ADD KEY `lng` (`lng`),
		ADD KEY `cos_lat` (`cos_lat`),
		ADD KEY `sin_lat` (`sin_lat`)
""")

mysql.execute("""
	CREATE TABLE `hoodsv2` (
		`id` int(10) UNSIGNED NOT NULL,
		`name` varchar(30) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
		`net` varchar(30) COLLATE utf8_unicode_ci NOT NULL,
		`lat` double DEFAULT NULL,
		`lng` double DEFAULT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `hoodsv2`
		ADD PRIMARY KEY (`id`),
		ADD UNIQUE KEY `name` (`name`),
		ADD KEY `lat` (`lat`),
		ADD KEY `lng` (`lng`)
""")

mysql.execute("""
	CREATE TABLE `polygons` (
		`id` int(10) UNSIGNED NOT NULL,
		`polyid` int(10) UNSIGNED NOT NULL,
		`lat` double NOT NULL,
		`lon` double NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `polygons`
		ADD PRIMARY KEY (`id`),
		ADD KEY `polyid` (`polyid`)
""")

mysql.execute("""
	ALTER TABLE `polygons`
		MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT
""")

mysql.execute("""
	CREATE TABLE `polyhoods` (
		`polyid` int(10) UNSIGNED NOT NULL,
		`hoodid` int(10) UNSIGNED NOT NULL
	) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `polyhoods`
		ADD PRIMARY KEY (`polyid`)
""")

mysql.execute("""
	ALTER TABLE `polyhoods`
		MODIFY `polyid` int(10) UNSIGNED NOT NULL AUTO_INCREMENT
""")

mysql.commit()

mysql.close()
