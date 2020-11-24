#!/usr/bin/python3

# Execute manually

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.misc import defrag_all
from ffmap.mysqltools import FreifunkMySQL

import time
start_time = time.time()

mysql = FreifunkMySQL()
defrag_all(mysql)
mysql.close()

print("--- Total defrag duration: %.3f seconds ---" % (time.time() - start_time))
