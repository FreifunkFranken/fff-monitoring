#!/bin/bash

for mac in `cat /home/dominik/alfred_legacy_provider/macs.txt` ; do
	echo "Crawling $mac"
	/home/dominik/alfred_legacy_provider/crawl.py $mac
done
