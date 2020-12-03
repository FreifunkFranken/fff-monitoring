## Git Repository Logic
* Frequent updates are made to the **testing** branch, which is considered "dirty". Commits appearing here may be quickly written, untested, incomplete, etc. This is where the development happens.
* In unspecified intervals, the piled-up changes in the testing branch are reviewed, ordered and squashed to a smaller set of tidy commits. Those are then pushed to the **master** branch.
* The tidy-up is marked by an empty commit "Realign with master" in the testing branch. This is roughly equivalent to a *merge*, although for an actual merge the commits would remain unaltered.
* Development happens in the testing branch. Thus, *testing* is more up-to-date, but *master* is better to understand.
* The Monitoring web server uses the testing branch.


## Debian Dependencies
```bash
apt-get install mariadb-server memcached python3-memcache python3-mysqldb python python3 python3-requests python3-lxml python3-pip python3-flask python3-dateutil python3-numpy python3-scipy python3-mapnik python3-pip uwsgi-plugin-python3 nginx git influxdb curl
pip3 install wheel pymongo pillow modestmaps simplejson werkzeug tilestache influxdb
```

## Prerequisites
* Datenbank in MySQL anlegen
* Git vorbereiten:
```bash
git clone https://github.com/FreifunkFranken/fff-monitoring
git clone https://github.com/TileStache/TileStache
cd fff-monitoring
cp ffmap/mysqlconfig.example.py ffmap/mysqlconfig.py
```
* MySQL Zugangsdaten in mysqlconfig.py eintragen

## InfluxDB
```
cp ffmap/influconfig.example.py ffmap/influconfig.py

curl -X POST -G "http://localhost:8086/query?" --data-urlencode "q=CREATE DATABASE databasename"
curl -X POST -G "http://localhost:8086/query?" --data-urlencode "q=CREATE USER username WITH PASSWORD 'password'"
curl -X POST -G "http://localhost:8086/query?" --data-urlencode "q=GRANT ALL ON databasename TO username"
```

Bitte beachtet das in der Datei /ffmap/influxtools.py die Datenbank statisch angesprochen wird. Ihr sollten also, falls ihr einen anderen DB Namen als "fff-monitoring" nutzen wollt, hier entsprechend anpassen.

Authentifizierung in Datei /etc/influxdb/influxdb.conf aktivieren

```auth-enabled = true```

Dienst neu starten

```systemctl restart influxdb```

Zugangsdaten in der Config hinterlegen

## Installation
```bash
./install.sh
systemctl daemon-reload
systemctl enable uwsgi-ffmap
systemctl enable uwsgi-tiles
systemctl start uwsgi-ffmap
systemctl start uwsgi-tiles
cd ffmap/db/
./init_mysql.py
./init_influx.py
# Then apply NGINX Config
cd ../.. # go back to fff-monitoring root directory
./scripts/setupcron.sh
```

## NGINX Config
```nginx
server {
	listen 443 ssl default_server;
	listen [::]:443 ssl default_server;

...

	location / {
		include uwsgi_params;
		uwsgi_pass 127.0.0.1:3031;
		client_max_body_size 30M;
	}

	location /tiles {
		include uwsgi_params;
		uwsgi_pass 127.0.0.1:3032;
	}
	
	location /static/ {
		root /usr/share/ffmap/;
		expires max;
		add_header Cache-Control "public";
	}

...

}
```

## Admin anlegen
* User über WebUI anlegen
* Dann über z.B. phpmyadmin in der Tabelle users 'admin' auf 1 setzen
