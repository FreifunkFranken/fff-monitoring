#!/bin/bash

mkdir -vp /var/lib/ffmap/csv
#FIXME: create dummy csv files
chown -R www-data:www-data /var/lib/ffmap

mkdir -vp /usr/share/ffmap
cp -v ffmap/mapnik/{hoods,links_and_routers}.xml /usr/share/ffmap
sed -i -e 's#>csv/#>/var/lib/ffmap/csv/#' /usr/share/ffmap/{hoods,links_and_routers}.xml
chown www-data:www-data /usr/share/ffmap/{hoods,links_and_routers}.xml
cp -v ffmap/wsgi/{hoods,links_and_routers,web}.wsgi /usr/share/ffmap
cp -rv ffmap/web/static /usr/share/ffmap
cp -rv ffmap/web/templates /usr/share/ffmap

mkdir -vp /var/cache/tiles/{hoods,links_and_routers}
chown -R www-data:www-data /var/cache/tiles/

cp -v ffmap/systemd/*.service /etc/systemd/system/
systemctl daemon-reload

python3 setup.py install
