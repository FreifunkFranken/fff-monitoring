#!/bin/sh
#
# Gateway data script for FFF Monitoring
# Copyright Adrian Schmutzler, 2018.
# License GPLv3
#
# designed for GATEWAY FIRMWARE
#
# v1.4.7 - 2021-02-22
# - Use br-client instead of br-mesh
#
# v1.4.6 - 2018-10-17
# - Fix IPv4/IPv6 sed (leading space in match pattern)
#
# v1.4.3 - 2018-08-28
# - Added version to json
# - GW-Firmware: Only append IPv4/IPv6/DHCP to bat0
#
# v1.4.2 - 2018-08-28
# - Fixed IPv4 sed to ignore subnet mask
# - Check for multiple IPv6 addresses
# - GW-Firmware: Ignore wireless devices
# - GW-Firmware: Use eth device from batctl if
# - GW-Firmware: Use only br-mesh for batctl if
# - GW-Firmware: Select fd43 address with ::
# - GW-Firmware: Adjust DHCP to uci
#
# v1.4.1 - 2018-08-25
# - Fixed greps for IPv4/IPv6/dnsmasq
#
# v1.4 - 2018-08-23
# - Transmit internal IPv4/IPv6
# - Transmit DHCP range for dnsmasq
#
# v1.3 - 2018-08-23
# - Support multiple Monitoring URLs
# - Use https by default
# - Changed batctl default path
#
# v1.2.1 - 2018-01-12
# - Added "grep fff" to support L2TP
#
# v1.2 - 2018-01-12
# - Added batctl command and vpnif
#
# v1.1 - 2018-01-12
# - Initial Version
#

# Config
api_urls="https://monitoring.freifunk-franken.de/api/gwinfo" # space-separated list of addresses (api_urls="url1 url2")
batctlpath=/usr/sbin/batctl
brif=br-client
hostname="$(uci -q get system.@system[0].hostname)"
statslink="$(uci -q get gateway.@gateway[0].statslink)"

# Code
tmp=$(/bin/mktemp)
echo "{\"version\":\"1.4.6\",\"hostname\":\"$hostname\",\"stats_page\":\"$statslink\",\"netifs\":[" > $tmp

comma=""
for netif in $(ls /sys/class/net); do
	if [ "$netif" = "lo" ] || echo "$netif" | grep -q "w" ; then # remove wXap, wXmesh, etc.
		continue
	fi
	mac="$(cat "/sys/class/net/$netif/address")"
	batctl="$("$batctlpath" -m "$netif" if | grep "eth" | sed -n 's/:.*//p')"

	ipv4=""
	ipv6=""
	dhcpstart=""
	dhcpend=""
	if [ "$netif" = "bat0" ]; then
		ipv4="$(ip -4 addr show dev "$brif" | grep " 10\." | sed 's/.* \(10\.[^ ]*\/[^ ]*\) .*/\1/')"
		ipv6="$(ip -6 addr show dev "$brif" | grep " fd43" | grep '::' | sed 's/.* \(fd43[^ ]*\) .*/\1/')"
		[ "$(echo "$ipv6" | wc -l)" = "1" ] || ipv6=""
		dhcpstart="$(uci -q get dhcp.client.start)"
	fi

	echo "$comma{\"mac\":\"$mac\",\"netif\":\"$netif\",\"vpnif\":\"$batctl\",\"ipv4\":\"$ipv4\",\"ipv6\":\"$ipv6\",\"dhcpstart\":\"$dhcpstart\",\"dhcpend\":\"$dhcpend\"}" >> $tmp
	comma=","
done

echo "],\"admins\":[" >> $tmp

comma=""
for admin in $(uci -q get gateway.@gateway[0].admin); do
	echo "$comma\"$admin\"" >> $tmp && comma=","
done

echo "]}" >> $tmp

for api_url in $api_urls; do
	/usr/bin/curl -k -v -H "Content-type: application/json; charset=UTF-8" -X POST --data-binary @$tmp $api_url
done
/bin/rm "$tmp"
