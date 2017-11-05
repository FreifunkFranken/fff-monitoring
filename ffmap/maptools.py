#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL

import math
import numpy as np
from scipy.spatial import Voronoi

import urllib.request, json

CONFIG = {
	"csv_dir": "/var/lib/ffmap/csv"
}

EARTH_RADIUS = 6378137.0

def touch(fname, times=None):
	with open(fname, 'a'):
		os.utime(fname, times)

def merc_sphere(lng, lat):
	x = math.radians(lng) * EARTH_RADIUS
	y = math.log(math.tan(math.pi/4 + math.radians(lat)/2)) * EARTH_RADIUS
	return (x,y)

def merc_sphere_inv(x, y):
	lng = math.degrees(x / EARTH_RADIUS)
	lat = math.degrees(2*math.atan(math.exp(y / EARTH_RADIUS)) - math.pi/2)
	return (lng,lat)

def draw_voronoi_lines(csv, hoods):
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


def update_mapnik_csv(mysql):
	with open(os.path.join(CONFIG["csv_dir"], "routers.csv"), "w") as csv:
		csv.write("lng,lat,status\n")
		routers = mysql.fetchall("""
			SELECT status, lat, lng FROM router
			WHERE lat IS NOT NULL AND lng IS NOT NULL
		""")
		for router in routers:
			csv.write("%f,%f,%s\n" % (
				router["lng"],
				router["lat"],
				router["status"]
			))

	dblinks = mysql.fetchall("""
		SELECT r1.lat AS rlat, r1.lng AS rlng, r2.lat AS nlat, r2.lng AS nlng, n.type AS type, quality
		FROM router AS r1
		INNER JOIN router_neighbor AS n ON r1.id = n.router
		INNER JOIN (
			SELECT router, mac FROM router_netif GROUP BY mac, router
			) AS net ON n.mac = net.mac
		INNER JOIN router AS r2 ON net.router = r2.id
		WHERE r1.lat IS NOT NULL AND r1.lng IS NOT NULL AND r2.lat IS NOT NULL AND r2.lng IS NOT NULL
		AND r1.status = 'online'
	""")
	links = []
	linksl3 = []
	for row in dblinks:
		if row.get("type")=="l3":
			linksl3.append((
				row["rlng"],
				row["rlat"],
				row["nlng"],
				row["nlat"]
			))
		else:
			links.append((
				row["rlng"],
				row["rlat"],
				row["nlng"],
				row["nlat"],
				row["quality"]
			))
	with open(os.path.join(CONFIG["csv_dir"], "links.csv"), "w") as csv:
		csv.write("WKT,quality\n")
		for link in sorted(links, key=lambda l: l[4]):
			csv.write("\"LINESTRING (%f %f,%f %f)\",%i\n" % link)

	with open(os.path.join(CONFIG["csv_dir"], "l3_links.csv"), "w") as csv:
		csv.write("WKT\n")
		for link in linksl3:
			csv.write("\"LINESTRING (%f %f,%f %f)\"\n" % link)

	dbhoods = mysql.fetchall("""
		SELECT name, lat, lng FROM hoods
		WHERE lat IS NOT NULL AND lng IS NOT NULL
	""")
	with open(os.path.join(CONFIG["csv_dir"], "hood-points.csv"), "w", encoding="UTF-8") as csv:
		csv.write("lng,lat,name\n")
		for hood in dbhoods:
			csv.write("%f,%f,\"%s\"\n" % (
				hood["lng"],
				hood["lat"],
				hood["name"]
			))

	with open(os.path.join(CONFIG["csv_dir"], "hoods.csv"), "w") as csv:
		csv.write("WKT\n")
		hoods = []
		for hood in dbhoods:
			# convert coordinates info marcator sphere as voronoi doesn't work with lng/lat
			x, y = merc_sphere(hood["lng"], hood["lat"])
			hoods.append([x, y])
		draw_voronoi_lines(csv, hoods)

	with urllib.request.urlopen("http://keyserver.freifunk-franken.de/v2/hoods.php") as url:
		dbhoodsv2 = json.loads(url.read().decode())
	
	with open(os.path.join(CONFIG["csv_dir"], "hood-points-v2.csv"), "w", encoding="UTF-8") as csv:
		csv.write("lng,lat,name\n")
		
		for hood in dbhoodsv2:
			if not ( 'lon' in hood and 'lat' in hood ):
				continue
			csv.write("%f,%f,\"%s\"\n" % (
				hood["lon"],
				hood["lat"],
				hood["name"]
			))

	with open(os.path.join(CONFIG["csv_dir"], "hoodsv2.csv"), "w") as csv:
		csv.write("WKT\n")
		hoods = []
		
		for hood in dbhoodsv2:
			if not ( 'lon' in hood and 'lat' in hood ):
				continue
			# convert coordinates info marcator sphere as voronoi doesn't work with lng/lat
			x, y = merc_sphere(hood["lon"], hood["lat"])
			hoods.append([x, y])
		draw_voronoi_lines(csv, hoods)

	# touch mapnik XML files to trigger tilelite watcher
	touch("/usr/share/ffmap/hoods.xml")
	touch("/usr/share/ffmap/hoodsv2.xml")
	touch("/usr/share/ffmap/links_and_routers.xml")

if __name__ == '__main__':
	update_mapnik_csv()
