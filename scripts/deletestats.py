#!/usr/bin/python3

# Execute once daily, also 2 min after full 5 mins (so it does not coincide with alfred)

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.routertools import delete_old_stats
from ffmap.mysqltools import FreifunkMySQL

import time
start_time = time.time()

mysql = FreifunkMySQL()
delete_old_stats(mysql)
mysql.close()

print("--- Total duration: %s seconds ---" % (time.time() - start_time))
