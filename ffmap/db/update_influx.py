#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.influxtools import influ_set_retention, influ_policies
from getpass import getpass

policies = influ_policies()

if len(sys.argv) > 1:
	# read password for user input
	pw = getpass()
	influ_set_retention(True,policies,sys.argv[1],pw)
else:
	influ_set_retention(True,policies)
