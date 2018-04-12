#!/usr/bin/python3

# Execute manually

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.misc import defrag_table, writelog
from ffmap.config import CONFIG
from ffmap.mysqltools import FreifunkMySQL

import time
start_time = time.time()

mysql = FreifunkMySQL()
i = 1
while i < len(sys.argv):
	defrag_table(mysql,sys.argv[i],1)
	i = i + 1
mysql.close()

writelog(CONFIG["debug_dir"] + "/deletetime.txt", "-------")
print("--- Total defrag duration: %.3f seconds ---" % (time.time() - start_time))
