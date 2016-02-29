#!/bin/bash

MYSQL_PWD="`grep mysql_password /var/www/netmon/config/config.local.inc.php | cut -d '"' -f 2`"
mysql -u netmon -"p$MYSQL_PWD" netmon -e 'SELECT r.id, r.hostname, c.firmware_version, i.name, i.mac_addr FROM routers r JOIN crawl_routers c ON c.id = (SELECT MAX(id) FROM crawl_routers WHERE router_id = r.id) LEFT JOIN crawl_interfaces i ON i.id = (SELECT MAX(id) FROM crawl_interfaces WHERE router_id = r.id AND name = "br-mesh") WHERE c.status = "online" AND c.firmware_version <= "0.5.0" ORDER BY r.id;';
