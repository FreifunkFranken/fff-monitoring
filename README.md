## Installation
```bash
./install.sh
systemctl daemon-reload
systemctl enable mongodb
systemctl enable uwsgi-ffmap
systemctl enable uwsgi-tiles-links_and_routers
systemctl enable uwsgi-tiles-hoods
systemctl start mongodb
systemctl start uwsgi-ffmap
systemctl start uwsgi-tiles-links_and_routers
systemctl start uwsgi-tiles-hoods
# Then apply NGINX Config
```

## Debian Dependencies
```bash
apt-get install python python3 mongodb python3-requests python3-lxml python3-pip python3-flask python3-dateutil python3-numpy python3-scipy python-mapnik python3-pip uwsgi-plugin-python uwsgi-plugin-python3 nginx tilestache
pip3 install pymongo
```

## NGINX Config
```nginx
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
...
```
