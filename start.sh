#!/bin/bash

printf "\nStarting ...\n\n"
systemctl start uwsgi-ffmap
systemctl start uwsgi-tiles
