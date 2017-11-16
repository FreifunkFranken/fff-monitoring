#!/bin/sh

monpath=/data/fff/fff-monitoring

if crontab -l | grep -q "$monpath" ; then
	echo "Cron already set."
	exit 1
fi

# Runs every 5 min and waits 2 min
(crontab -l 2>/dev/null; echo "2-59/5 * * * * $monpath/scripts/calcglobalstats.py") | crontab -

# Runs at 4:02
(crontab -l 2>/dev/null; echo "2 4 * * * $monpath/scripts/deletestats.py") | crontab -

echo "Cron set successfully."
exit 0

