#!/usr/bin/python3

# Execute manually

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.hoodtools import update_hoods_poly
from ffmap.mysqltools import FreifunkMySQL

mysql = FreifunkMySQL()
update_hoods_poly(mysql)
mysql.commit()
mysql.close()
