#!/usr/bin/python

import requests
import subprocess

# doku: https://developers.google.com/maps/documentation/geolocation/intro#wifi_access_point_object

"""
r = requests.post("https://www.googleapis.com/geolocation/v1/geolocate", params={"key": "AIzaSyDwr302FpOSkGRpLlUpPThNTDPbXcIn_FM"}, json={
    "wifiAccessPoints": [
        {
            "macAddress": "10-fe-ed-af-43-44",
            "signalStrength": 100
        },
        {
            "macAddress": "02-ca-ff-ee-ba-be",
            "signalStrength": 100
        }
	]
})
print(r.text)
"""

networks = []

o = subprocess.check_output(["iwlist", "wlan0", "scanning"])
ls = o.decode("UTF-8").split("          Cell")
for wifi in ls[1:]:
	for field in wifi.split("\n"):
		if "Address:" in field:
			mac = field.split("Address: ")[1]
		elif "Signal level=" in field:
			signal_strength = field.split("Signal level=")[1].split(" dBm")[0]
	print("%s -> %s" % (mac, signal_strength))
	networks.append({"macAddress": mac, "signalStrength": signal_strength})

r = requests.post("https://www.googleapis.com/geolocation/v1/geolocate",
	params={"key": "AIzaSyDwr302FpOSkGRpLlUpPThNTDPbXcIn_FM"},
	json={"wifiAccessPoints": networks}
)

print({"wifiAccessPoints": networks})
print(r.text)
