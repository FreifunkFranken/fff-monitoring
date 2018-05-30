#!/bin/sh

command="systemctl restart uwsgi-tiles"
append="2>&1 | /usr/bin/logger -t uwsgi-tiles"

if crontab -l | grep -q "$command" ; then
	echo "Cron already set."
	exit 1
fi

# Runs at X:14
(crontab -l 2>/dev/null; echo "14 * * * * $command $append") | crontab -

echo "Cron set successfully."
exit 0

