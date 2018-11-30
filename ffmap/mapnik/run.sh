#!/bin/bash

liteserv.py routers.xml --processes=5 &
liteserv.py routers_v2.xml -p 8003 --processes=5 &
liteserv.py routers_local.xml -p 8004 --processes=5 &
liteserv.py hoods_v2.xml -p 8002 --processes=5
liteserv.py hoods_poly.xml -p 8005 --processes=5

killall liteserv.py
