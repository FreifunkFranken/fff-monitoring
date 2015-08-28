#!/bin/bash

# make sure to install mapnik, tilelite and lxml

#curl -s "https://netmon.freifunk-franken.de/api.php?class=ApiMap&section=batman_advanced_conn_nexthop" > links.kml
# replace <kml foo=bar> with <kml> to make xml parser work
#./p.py
liteserv.py links.xml
# firefox l.html
