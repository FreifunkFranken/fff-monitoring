#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()

mysql.execute("""
	CREATE TABLE `users` (
		`id` int(11) NOT NULL,
		`nickname` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`password` varchar(250) COLLATE utf8_unicode_ci DEFAULT NULL,
		`token` varchar(250) COLLATE utf8_unicode_ci DEFAULT NULL,
		`email` varchar(200) COLLATE utf8_unicode_ci NOT NULL,
		`created` datetime NOT NULL,
		`admin` tinyint(4) NOT NULL DEFAULT '0'
	)
	ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci
""")

mysql.execute("""
	ALTER TABLE `users`
		ADD PRIMARY KEY (`id`),
		ADD KEY `nickname` (`nickname`),
		ADD KEY `email` (`email`)
""")

mysql.execute("""
	ALTER TABLE `users`
		MODIFY `id` int(11) NOT NULL AUTO_INCREMENT
""")

mysql.close()
