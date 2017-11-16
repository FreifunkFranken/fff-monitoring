#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.routertools import *
from ffmap.maptools import *
from ffmap.mysqltools import FreifunkMySQL
from ffmap.stattools import record_global_stats, record_hood_stats

mysql = FreifunkMySQL()
detect_offline_routers(mysql)
detect_orphaned_routers(mysql)
delete_orphaned_routers(mysql)
delete_old_stats(mysql)
record_global_stats(mysql)
record_hood_stats(mysql)
update_mapnik_csv(mysql)
mysql.close()
