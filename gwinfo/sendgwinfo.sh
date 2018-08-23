#!/bin/sh
#
# Gateway data script for FFF Monitoring
# Copyright Adrian Schmutzler, 2018.
# License GPLv3
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
batctlpath=/usr/sbin/batctl # Adjust to YOUR path!
hostname="MyHost"
admin1="Admin"
admin2=
admin3=
statslink="" # Provide link to stats page (MRTG or similar)
dhcp=1 # 0=disabled, 1=dnsmasq, 2=isc-dhcp-server

# Code
tmp=$(/bin/mktemp)
echo "{\"hostname\":\"$hostname\",\"stats_page\":\"$statslink\",\"netifs\":[" > $tmp

comma=""
for netif in $(ls /sys/class/net); do
	if [ "$netif" = "lo" ] ; then
		continue
	fi
	mac="$(cat "/sys/class/net/$netif/address")"
	batctl="$("$batctlpath" -m "$netif" if | grep "fff" | sed -n 's/:.*//p')"

	ipv4="$(ip -4 addr show dev "$netif" | grep "10\." | sed 's/.*\(10\.[^ ]*\) .*/\1/')"
	ipv6="$(ip -6 addr show dev "$netif" | grep "fd43" | sed 's/.*\(fd43[^ ]*\) .*/\1/')"

	if [ "$dhcp" = "1" ]; then
			dhcpdata="$(ps ax | grep "dnsmasq" | grep "$netif" | sed 's/.*dhcp-range=\([^ ]*\) .*/\1/')"
			dhcpstart="$(echo "$dhcpdata" | cut -d',' -f1)"
			dhcpend="$(echo "$dhcpdata" | cut -d',' -f2)"
	#elif [ "$dhcp" = "2" ]; then
			# not implemented
	fi

	echo "$comma{\"mac\":\"$mac\",\"netif\":\"$netif\",\"vpnif\":\"$batctl\",\"ipv4\":\"$ipv4\",\"ipv6\":\"$ipv6\",\"dhcpstart\":\"$dhcpstart\",\"dhcpend\":\"$dhcpend\"}" >> $tmp
	comma=","
done

echo "],\"admins\":[" >> $tmp

comma=""
[ -n "$admin1" ] && echo "\"$admin1\"" >> $tmp && comma=","
[ -n "$admin2" ] && echo "$comma\"$admin2\"" >> $tmp && comma=","
[ -n "$admin3" ] && echo "$comma\"$admin3\"" >> $tmp

echo "]}" >> $tmp

for api_url in $api_urls; do
	/usr/bin/curl -k -v -H "Content-type: application/json; charset=UTF-8" -X POST --data-binary @$tmp $api_url
done
/bin/rm "$tmp"
