#!/usr/bin/python

"""
To setup TileLite on a production server using Apache and ModWSGI
create a virtualhost or otherwise insert the WSGI configuration into
your Apache configuration like so:

    WSGIScriptAlias /<url> /path/to/this/tilelite.wsgi
    WSGIDaemonProcess <process name> user=<user> group=<group> processes=10 threads=1
    WSGIProcessGroup <process name>

 * 'tilelite.wsgi' is the name of the simple python script below that associates the 
   tilelite.Server instance with a Mapnik xml file. It can be named anything you like
   but should end with either a '.wsgi' or '.py' extension.
    
 * <url> can be either be '/' (to mount the script at http://yourserver.com/) or it can be 
   a path such as '/tiles' to mount the server at http://yourserver.com/tiles

 * <process name> can be any unique name like 'tileliteserver'

 * <user> and <group> should be a unix user that has permissions to the 'tilelite.wsgi'

 * Note: this is a multiprocess (not threaded) server so you *can* set 'processes' >= 1
   but threads *must be* == 1, otherwise this server will not work within Apache.

An example setup would be:

    ## TileLite sample setup ##
    WSGIScriptAlias /tiles /home/mapnik/projects/tilelite/tilelite.wsgi
    WSGIDaemonProcess tileliteserver user=www-data group=www-data processes=10 threads=1
    WSGIProcessGroup tileliteserver

Next, edit the script code below and place it where the WSGIScriptAlias path points to.

Then test your apache configuration and restart. On debian linux this might look like:

    $ sudo apache2ctl configtest
    $ /etc/init.d/apache restart

Then go to:

    http://yourserver.com/tiles/
    
"""

from tilelite import Server

options = {
	'watch_mapfile': True,
	'paletted': False,
	'cache_force': False,
	'format': 'png',
	'max_failures': 6,
	'max_zoom': 22,
	'debug': True,
	'cache_path': '/var/cache/tiles/links_and_routers/',
	'watch_interval': 2,
	'caching': True,
	'buffer_size': 128,
	'size': 256
}

# note: this variable must be called 'application'
application = Server('/usr/share/ffmap/links_and_routers.xml', options=options)
