#!/bin/bash

printf "\nStopping ...\n\n"
systemctl stop uwsgi-tiles
systemctl stop uwsgi-ffmap
