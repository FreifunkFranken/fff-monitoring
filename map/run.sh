#!/bin/bash

liteserv.py links.xml &
liteserv.py routers.xml -p 8001

killall liteserv.py
