#!/usr/bin/python3

from distutils.core import setup

setup(                                                                                                                                         
	name='ffmap',
	version='0.0.1',
	license='GPL',
	description='FF-MAP',
	author='Dominik Heidler',
	author_email='dominik@heidler.eu',
	url='http://github.com/asdil12/ff-map',
	#requires=['flask', 'flup'],
	packages=['ffmap', 'ffmap.web'],
	#scripts=['bin/aurbs'],
	#data_files=[
	#	('/etc', ['templates/aurbs.yml']),
	#	('/usr/share/aurbs/cfg', ['templates/gpg.conf']),
	#	('/usr/share/doc/aurbs', ['templates/lighttpd.conf.sample']),
	#],
)

