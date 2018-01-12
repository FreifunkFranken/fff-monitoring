#!/usr/bin/python3

# Deletes unlinked rows from gw_* and router_* tables

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.routertools import delete_unlinked_routers
from ffmap.gwtools import delete_unlinked_gws
from ffmap.mysqltools import FreifunkMySQL

import time
start_time = time.time()

mysql = FreifunkMySQL()
delete_unlinked_routers(mysql)
delete_unlinked_gws(mysql)
mysql.close()

print("\n--- Total duration: %.3f seconds ---\n" % (time.time() - start_time))
