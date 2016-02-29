#!/bin/bash

/home/dominik/alfred_legacy_provider/list_old.sh 2>/dev/null | grep br-mesh | awk -F ' ' '{print $NF}' > /home/dominik/alfred_legacy_provider/macs.txt
