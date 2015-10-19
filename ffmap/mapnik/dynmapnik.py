#!/usr/bin/python2

import os
import logging
import TileStache

class DynMapnik(TileStache.Providers.Mapnik):
	def __init__(self, *args, **kwargs):
		self.mapfile_mtime = 0
		TileStache.Providers.Mapnik.__init__(self, *args, **kwargs)
	def renderArea(self, *args, **kwargs):
		cur_mapfile_mtime = os.path.getmtime(self.mapfile)
		if cur_mapfile_mtime > self.mapfile_mtime:
			self.mapfile_mtime = cur_mapfile_mtime
			if self.mapnik is not None:
				self.mapnik = None
				logging.info('TileStache.DynMapnik.ImageProvider.renderArea() detected mapfile change')
		return TileStache.Providers.Mapnik.renderArea(self, *args, **kwargs)
