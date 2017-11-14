#!/bin/bash

mkdir -vp /var/lib/ffmap/csv
#FIXME: create dummy csv files
chown -R www-data:www-data /var/lib/ffmap

mkdir -vp /usr/share/ffmap
cp -v ffmap/mapnik/{hoods,hoodsv2,links_and_routers}.xml /usr/share/ffmap
sed -i -e 's#>csv/#>/var/lib/ffmap/csv/#' /usr/share/ffmap/{hoods,hoodsv2,links_and_routers}.xml
chown www-data:www-data /usr/share/ffmap/{hoods,hoodsv2,links_and_routers}.xml

cp -v ffmap/mapnik/tilestache.cfg /usr/share/ffmap
cp -rv ffmap/web/static /usr/share/ffmap
cp -rv ffmap/web/templates /usr/share/ffmap

mkdir -vp /var/cache/ffmap/tiles/
chown -R www-data:www-data /var/cache/ffmap/tiles/

cp -v ffmap/systemd/*.service /etc/systemd/system/
systemctl daemon-reload

python3 setup.py install --force

(cd ffmap/mapnik; python3 setup.py install)
