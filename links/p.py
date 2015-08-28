#!/usr/bin/python

from lxml import etree

tree = etree.parse("links.kml")

csv = open("links.csv", "w")

csv.write("WKT,color\n")

for line in tree.xpath("//kml/Document/Folder/Placemark"):
	color = line.xpath("Style/LineStyle/color")[0].text
	coordinates = line.xpath("Polygon/outerBoundaryIs/LinearRing/coordinates")[0].text.replace("\n\t\t\t\t\t\t\t", " ")
	coordinates = coordinates.replace(",0", "")
	coordinates = coordinates.replace(",", "$").replace(" ", ",").replace("$", " ")
	csv.write("\"LINESTRING (%s)\",%s\n" % (coordinates, color))

csv.close()
