#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.dbtools import FreifunkDB

import math
import numpy as np
from scipy.spatial import Voronoi

db = FreifunkDB().handle()

CONFIG = {
	"csv_dir": "/var/lib/ffmap/csv"
}

def touch(fname, times=None):
	with open(fname, 'a'):
		os.utime(fname, times)

def update_mapnik_csv():
	with open(os.path.join(CONFIG["csv_dir"], "routers.csv"), "w") as csv:
		csv.write("lng,lat,status\n")
		for router in db.routers.find({"position.coordinates": {"$exists": True}}):
			csv.write("%f,%f,%s\n" % (
				router["position"]["coordinates"][0],
				router["position"]["coordinates"][1],
				router["status"]
			))

	with open(os.path.join(CONFIG["csv_dir"], "links.csv"), "w") as csv:
		csv.write("WKT,quality\n")
		for router in db.routers.find({"position.coordinates": {"$exists": True}, "neighbours": {"$exists": True}}):
			for neighbour in router["neighbours"]:
				if "position" in neighbour:
					csv.write("\"LINESTRING (%f %f,%f %f)\",%i\n" % (
						router["position"]["coordinates"][0],
						router["position"]["coordinates"][1],
						neighbour["position"]["coordinates"][0],
						neighbour["position"]["coordinates"][1],
						neighbour["quality"]
					))

	with open(os.path.join(CONFIG["csv_dir"], "hood-points.csv"), "w", encoding="UTF-8") as csv:
		csv.write("lng,lat,name\n")
		for hood in db.hoods.find({"position": {"$exists": True}}):
			csv.write("%f,%f,\"%s\"\n" % (
				hood["position"]["coordinates"][0],
				hood["position"]["coordinates"][1],
				hood["name"]
			))

	with open(os.path.join(CONFIG["csv_dir"], "hoods.csv"), "w") as csv:
		EARTH_RADIUS = 6378137.0

		def merc_sphere(lng, lat):
			x = math.radians(lng) * EARTH_RADIUS
			y = math.log(math.tan(math.pi/4 + math.radians(lat)/2)) * EARTH_RADIUS
			return (x,y)

		def merc_sphere_inv(x, y):
			lng = math.degrees(x / EARTH_RADIUS)
			lat = math.degrees(2*math.atan(math.exp(y / 6378137.0)) - math.pi/2)
			return (lng,lat)

		csv.write("WKT\n")
		hoods = []
		for hood in db.hoods.find({"position": {"$exists": True}}):
			# convert coordinates info marcator sphere as voronoi doesn't work with lng/lat
			x, y = merc_sphere(hood["position"]["coordinates"][0], hood["position"]["coordinates"][1])
			hoods.append([x, y])

		points = np.array(hoods)
		vor = Voronoi(points)
		#mp = voronoi_plot_2d(vor)
		#mp.show()

		lines = [vor.vertices[line] for line in vor.ridge_vertices if -1 not in line]

		for line in lines:
			x = [line[0][0], line[1][0]]
			y = [line[0][1], line[1][1]]
			for i in range(len(x)-1):
				# convert mercator coordinates back into lng/lat
				lng1, lat1 = merc_sphere_inv(x[i], y[i])
				lng2, lat2 = merc_sphere_inv(x[i+1], y[i+1])
				csv.write("\"LINESTRING (%f %f,%f %f)\"\n" % (lng1, lat1, lng2, lat2))

		ptp_bound = np.array(merc_sphere(180, 360))
		center = vor.points.mean(axis=0)

		for pointidx, simplex in zip(vor.ridge_points, vor.ridge_vertices):
			simplex = np.asarray(simplex)
			if np.any(simplex < 0):
				i = simplex[simplex >= 0][0]  # finite end Voronoi vertex

				t = vor.points[pointidx[1]] - vor.points[pointidx[0]]  # tangent
				t /= np.linalg.norm(t)
				n = np.array([-t[1], t[0]])  # normal

				midpoint = vor.points[pointidx].mean(axis=0)
				direction = np.sign(np.dot(midpoint - center, n)) * n
				far_point = vor.vertices[i] + direction * ptp_bound.max()

				# convert mercator coordinates back into lng/lat
				lng1, lat1 = merc_sphere_inv(vor.vertices[i,0], vor.vertices[i,1])
				lng2, lat2 = merc_sphere_inv(far_point[0], far_point[1])
				csv.write("\"LINESTRING (%f %f,%f %f)\"\n" % (lng1, lat1, lng2, lat2))

	# touch mapnik XML files to trigger tilelite watcher
	touch("/usr/share/ffmap/hoods.xml")
	touch("/usr/share/ffmap/links_and_routers.xml")
