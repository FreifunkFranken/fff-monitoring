#!/usr/bin/python3

# Execute every 5 min, 2 mins after alfred comes in (sleep 120 in cron)

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.routertools import *
from ffmap.maptools import *
from ffmap.mysqltools import FreifunkMySQL
from ffmap.stattools import record_global_stats, record_hood_stats, record_gw_stats
from ffmap.hoodtools import update_hoods_v2

import time
start_time = time.time()

mysql = FreifunkMySQL()
detect_offline_routers(mysql)
detect_orphaned_routers(mysql)
delete_orphaned_routers(mysql)
#delete_old_stats(mysql) # Only execute once daily, takes 2 minutes
update_hoods_v2(mysql)
record_global_stats(mysql)
record_hood_stats(mysql)
record_gw_stats(mysql)
update_mapnik_csv(mysql)
mysql.close()

print("--- %.3f seconds ---" % (time.time() - start_time))
