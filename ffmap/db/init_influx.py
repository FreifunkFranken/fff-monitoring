#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.influxtools import FreifunkInflux

policies = {
	"router_default": 90,
	"router_neighbor": 90,
	"router_netif": 90,
	"router_gw": 90,
	"global_default": 90,
	"global_gw": 90,
	"global_hoods": 90
	}

influ = FreifunkInflux()

for k, v in policies.items():
	influ.query('CREATE RETENTION POLICY {} ON "fff-monitoring" DURATION {}d REPLICATION 1'.format(k,v))

influ.close()