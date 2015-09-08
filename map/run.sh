#!/bin/bash

liteserv.py links.xml &
liteserv.py routers.xml -p 8001 &
liteserv.py hoods.xml -p 8002

killall liteserv.py
