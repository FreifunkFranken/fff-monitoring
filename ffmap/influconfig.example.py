#!/usr/bin/python3

infludata = {
	"host":"localhost",
	"port":8086,
	"user":"username",
	"pw":"password",
	"db":"database"
	}

influpolicies = {
	"router_default":  60,
	"router_neighbor": 60,
	"router_netif":    60,
	"router_gw":       10,
	"global_default":  180,
	"global_gw":       180,
	"global_hoods":    180
	}
