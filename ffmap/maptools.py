#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL
from ffmap.config import CONFIG

import math
import numpy as np
from scipy.spatial import Voronoi

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
	routers = mysql.fetchall("""
		SELECT router.status, router.lat, router.lng, router.wan_uplink, v2, local FROM router
		WHERE router.lat IS NOT NULL AND router.lng IS NOT NULL
	""")

	rv1 = "lng,lat,status\n"
	rv2 = "lng,lat,status\n"
	rvlocal = "lng,lat,status\n"
	
	for router in routers:
		tmpstatus = router["status"]
		if router["wan_uplink"]:
			tmpstatus += "_wan";
		tmp = "%f,%f,%s\n" % (
			router["lng"],
			router["lat"],
			tmpstatus
		)
		if router["local"]:
			rvlocal += tmp
		elif router["v2"]:
			rv2 += tmp
		else:
			rv1 += tmp

	with open(os.path.join(CONFIG["csv_dir"], "routers.csv"), "w") as csv:
		csv.write(rv1)
	with open(os.path.join(CONFIG["csv_dir"], "routers_v2.csv"), "w") as csv:
		csv.write(rv2)
	with open(os.path.join(CONFIG["csv_dir"], "routers_local.csv"), "w") as csv:
		csv.write(rvlocal)

	dblinks = mysql.fetchall("""
		SELECT r1.id AS rid, r2.id AS nid, r1.lat AS rlat, r1.lng AS rlng, r2.lat AS nlat, r2.lng AS nlng, n.netif AS netif, n.type AS type, MAX(quality) AS quality, r1.v2, r1.local
		FROM router AS r1
		INNER JOIN router_neighbor AS n ON r1.id = n.router
		INNER JOIN (
			SELECT router, mac FROM router_netif GROUP BY mac, router
			) AS net ON n.mac = net.mac
		INNER JOIN router AS r2 ON net.router = r2.id
		WHERE r1.lat IS NOT NULL AND r1.lng IS NOT NULL AND r2.lat IS NOT NULL AND r2.lng IS NOT NULL
		AND r1.status = 'online'
		GROUP BY r1.id, r1.lat, r1.lng, r2.id, r2.lat, r2.lng, n.netif, n.type, r1.v2, r1.local
	""")
	links = []
	linksl3 = []
	linksv2 = []
	linksl3v2 = []
	linkslocal = []
	linksl3local = []
	dictl3 = {}
	dictl2 = {}
	# The following code is very ugly, but works and is not too slow. Maybe make it nicer at some point ...
	for row in dblinks:
		if row.get("type")=="l3":
			# Check for duplicate
			if row["nid"] in dictl3.keys() and row["rid"] in dictl3[row["nid"]]:
				continue
			# Write current set to dict
			if not row["rid"] in dictl3.keys():
				dictl3[row["rid"]] = []
			dictl3[row["rid"]].append(row["nid"])
			
			tmp = (
				row["rlng"],
				row["rlat"],
				row["nlng"],
				row["nlat"],
			)
			if row["local"]:
				linksl3local.append(tmp)
			elif row["v2"]:
				linksl3v2.append(tmp)
			else:
				linksl3.append(tmp)
		else:
			# Check for duplicate
			if row["nid"] in dictl2.keys() and row["rid"] in dictl2[row["nid"]].keys():
				oldqual = dictl2[row["nid"]][row["rid"]]["data"][4]
				# - Check for ethernet (ethernet always wins)
				# - Take maximum quality (thus continue if current is lower)
				if oldqual == 0 or oldqual > row["quality"]:
					continue
				# Delete old entry, as we create a new one with averaged quality
				del dictl2[row["nid"]][row["rid"]]
			if row["rid"] in dictl2.keys() and row["nid"] in dictl2[row["rid"]].keys():
				oldqual = dictl2[row["rid"]][row["nid"]]["data"][4]
				# - Check for ethernet (ethernet always wins)
				# - Take maximum quality (thus continue if current is lower)
				if oldqual == 0 or oldqual > row["quality"]:
					continue
				# No need to delete, since we overwrite later
			# Write current set to dict
			if not row["rid"] in dictl2.keys():
				dictl2[row["rid"]] = {}
			# Check for ethernet
			if row["netif"].startswith("eth"):
				row["quality"] = 0
			
			tmp = (
				row["rlng"],
				row["rlat"],
				row["nlng"],
				row["nlat"],
				row["quality"],
			)
			dictl2[row["rid"]][row["nid"]] = {'v2':row["v2"],'local':row["local"],'data':tmp}
	
	for d1 in dictl2.values():
		for d2 in d1.values():
			if d2["local"]:
				linkslocal.append(d2["data"])
			elif d2["v2"]:
				linksv2.append(d2["data"])
			else:
				links.append(d2["data"])
	
	with open(os.path.join(CONFIG["csv_dir"], "links.csv"), "w") as csv:
		csv.write("WKT,quality\n")
		for link in sorted(links, key=lambda l: l[4]):
			csv.write("\"LINESTRING (%f %f,%f %f)\",%i\n" % link)

	with open(os.path.join(CONFIG["csv_dir"], "links_v2.csv"), "w") as csv:
		csv.write("WKT,quality\n")
		for link in sorted(linksv2, key=lambda l: l[4]):
			csv.write("\"LINESTRING (%f %f,%f %f)\",%i\n" % link)

	with open(os.path.join(CONFIG["csv_dir"], "links_local.csv"), "w") as csv:
		csv.write("WKT,quality\n")
		for link in sorted(linkslocal, key=lambda l: l[4]):
			csv.write("\"LINESTRING (%f %f,%f %f)\",%i\n" % link)

	with open(os.path.join(CONFIG["csv_dir"], "l3_links.csv"), "w") as csv:
		csv.write("WKT\n")
		for link in linksl3:
			csv.write("\"LINESTRING (%f %f,%f %f)\"\n" % link)

	with open(os.path.join(CONFIG["csv_dir"], "l3_links_v2.csv"), "w") as csv:
		csv.write("WKT\n")
		for link in linksl3v2:
			csv.write("\"LINESTRING (%f %f,%f %f)\"\n" % link)

	with open(os.path.join(CONFIG["csv_dir"], "l3_links_local.csv"), "w") as csv:
		csv.write("WKT\n")
		for link in linksl3local:
			csv.write("\"LINESTRING (%f %f,%f %f)\"\n" % link)

	dbhoods = mysql.fetchall("""
		SELECT name, lat, lng FROM hoodsv1
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

	dbhoodsv2 = mysql.fetchall("""
		SELECT name, lat, lng FROM hoodsv2
		WHERE lat IS NOT NULL AND lng IS NOT NULL
	""")
	with open(os.path.join(CONFIG["csv_dir"], "hood-points-v2.csv"), "w", encoding="UTF-8") as csv:
		csv.write("lng,lat,name\n")
		for hood in dbhoodsv2:
			csv.write("%f,%f,\"%s\"\n" % (
				hood["lng"],
				hood["lat"],
				hood["name"]
			))

	with open(os.path.join(CONFIG["csv_dir"], "hoods_v2.csv"), "w") as csv:
		csv.write("WKT\n")
		hoods = []
		
		for hood in dbhoodsv2:
			# convert coordinates info marcator sphere as voronoi doesn't work with lng/lat
			x, y = merc_sphere(hood["lng"], hood["lat"])
			hoods.append([x, y])
		draw_voronoi_lines(csv, hoods)

	# touch mapnik XML files to trigger tilelite watcher
	touch("/usr/share/ffmap/hoods.xml")
	touch("/usr/share/ffmap/hoods_v2.xml")
	touch("/usr/share/ffmap/routers.xml")
	touch("/usr/share/ffmap/routers_v2.xml")
	touch("/usr/share/ffmap/routers_local.xml")

if __name__ == '__main__':
	update_mapnik_csv()
