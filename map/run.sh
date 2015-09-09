#!/bin/bash

liteserv.py links_and_routers.xml --processes=5 &
liteserv.py hoods.xml -p 8001 --processes=5

killall liteserv.py
