#!/bin/bash

printf "\nStopping ...\n\n"
systemctl stop uwsgi-tiles
systemctl stop uwsgi-ffmap

./install.sh

printf "\nStarting ...\n\n"
systemctl start uwsgi-ffmap
systemctl start uwsgi-tiles

printf "Done.\n\n"
