#!/bin/sh
#
# Gateway data script for FFF Monitoring
# Copyright Adrian Schmutzler, 2018.
# License GPLv3
#
# v1.2 - 2018-01-12
# - Added batctl command and vpnif
#
# v1.1 - 2018-01-12
# - Initial Version
#

# Config
#api_url="http://192.168.1.84/api/gwinfo"
api_url="http://monitoring.freifunk-franken.de/api/gwinfo"
batctlpath=/usr/local/sbin/batctl # Adjust to YOUR path!
hostname=testname
admin1="Admin"
admin2=
admin3=
statslink="http://adrianschmutzler.net/ip.php" # Provide link to stats page (MRTG or similar)
statslink=""

# Code
tmp=$(/bin/mktemp)
echo "{\"hostname\":\"$hostname\",\"stats_page\":\"$statslink\",\"netifs\":[" > $tmp

comma=""
for netif in $(ls /sys/class/net); do
	if [ "$netif" = "lo" ] ; then
		continue
	fi
	mac="$(cat "/sys/class/net/$netif/address")"
	batctl="$("$batctlpath" -m "$netif" if | sed -n 's/:.*//p')"
	echo "$comma{\"mac\":\"$mac\",\"netif\":\"$netif\",\"vpnif\":\"$batctl\"}" >> $tmp
	comma=","
done

echo "],\"admins\":[" >> $tmp

comma=""
[ -n "$admin1" ] && echo "\"$admin1\"" >> $tmp && comma=","
[ -n "$admin2" ] && echo "$comma\"$admin2\"" >> $tmp && comma=","
[ -n "$admin3" ] && echo "$comma\"$admin3\"" >> $tmp

echo "]}" >> $tmp


/usr/bin/curl -k -v -H "Content-type: application/json; charset=UTF-8" -X POST --data-binary @$tmp $api_url
/bin/rm "$tmp"
