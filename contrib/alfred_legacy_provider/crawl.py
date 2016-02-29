#!/usr/bin/python3

import sys
import subprocess
import re
import pyalfred



CONFIG = {
        #"crawl_outgoing_netif": "br-mesh",
	# this old system sucks
        "crawl_outgoing_netif": "25%s" % open("/sys/class/net/br-mesh/ifindex").read().strip(),
}

def mac_to_ipv6_linklocal(mac):
	# Remove the most common delimiters; dots, dashes, etc.
	mac_bare = re.sub('[%s]+' % re.escape(' .:-'), '', mac)
	mac_value = int(mac_bare, 16)

	# Split out the bytes that slot into the IPv6 address
	# XOR the most significant byte with 0x02, inverting the
	# Universal / Local bit
	high2 = mac_value >> 32 & 0xffff ^ 0x0200
	high1 = mac_value >> 24 & 0xff
	low1 = mac_value >> 16 & 0xff
	low2 = mac_value & 0xffff

	return 'fe80::{:04x}:{:02x}ff:fe{:02x}:{:04x}'.format(high2, high1, low1, low2)

mac = sys.argv[1]
fe80_ip = mac_to_ipv6_linklocal(mac)

node_data = subprocess.check_output(["curl", "-s", "--max-time", "5", "-g", "http://[%s%%%s]/node.data" % (
	fe80_ip,
	CONFIG["crawl_outgoing_netif"]
)])
try:
	node_data = gzip.decompress(node_data)
except:
	pass

assert "<TITLE>404" not in str(node_data).upper()


#print(node_data)

ac = pyalfred.AlfredConnection()
ac.send(64, node_data.decode("UTF-8", errors="replace"), mac, gzip_data=True)
