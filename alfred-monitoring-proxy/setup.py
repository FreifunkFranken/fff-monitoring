#!/usr/bin/python3

from distutils.core import setup

setup(
	name='alfred-monitoring-proxy',
	version='0.0.1',
	license='GPL',
	description='FFF ALFRED <--> Monitoring Proxy',
	author='Dominik Heidler',
	author_email='dominik@heidler.eu',
	url='http://github.com/asdil12/fff-monitoring',
	requires=['pyalfred'],
	scripts=['alfred-monitoring-proxy'],
)

