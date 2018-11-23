#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.web.api import api
from ffmap.web.filters import filters
from ffmap.mysqltools import FreifunkMySQL
from ffmap import stattools
from ffmap.usertools import *
from ffmap.routertools import delete_router, ban_router
from ffmap.gwtools import gw_name, gw_bat
from ffmap.web.helpers import *
from ffmap.config import CONFIG
from ffmap.misc import *

from flask import Flask, render_template, request, Response, redirect, url_for, flash, session
import bson
from bson.json_util import dumps as bson2json
from bson.objectid import ObjectId
import base64
import datetime

app = Flask(__name__)
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(filters)

tileurls = {
	"routers": "/tiles/routers",
	"routers_v2": "/tiles/routers_v2",
	"routers_local": "/tiles/routers_local",
	"hoods": "/tiles/hoods",
	"hoods_v2": "/tiles/hoods_v2",
}

@app.route('/')
def index():
	return render_template("index.html")

@app.route('/apidoc')
def apidoc():
	return render_template("apidoc.html")

@app.route('/map')
def router_map():
	return render_template("map.html", tileurls=tileurls)

@app.route('/routers')
def router_list():
	where, tuple, query_str = parse_router_list_search_query(request.args)
	mysql = FreifunkMySQL()
	
	routers = mysql.fetchall("""
		SELECT router.id, hostname, status, hoods.id AS hoodid, hoods.name AS hood, contact, nickname, hardware, router.created, sys_uptime, last_contact, clients, reset, blocked, v2, local
		FROM router
		INNER JOIN hoods ON router.hood = hoods.id
		LEFT JOIN users ON router.contact = users.email
		LEFT JOIN (
			SELECT router, blocked.mac AS blocked FROM router_netif
			INNER JOIN blocked ON router_netif.mac = blocked.mac
			WHERE netif = 'br-mesh'
		) AS b
		ON router.id = b.router
		{}
		ORDER BY hostname ASC
	""".format(where),tuple)
	mysql.close()
	routers = mysql.utcawaretuple(routers,"created")
	routers = mysql.utcawaretuple(routers,"last_contact")
	
	return render_template("router_list.html", query_str=query_str, routers=routers, numrouters=len(routers))

# test
@app.route('/v2routers')
def v2_routers():
	try:
		mysql = FreifunkMySQL()
		statsv2 = mysql.fetchall("""
			SELECT time, CAST(SUM(clients) AS SIGNED) clients, CAST(SUM(online) AS SIGNED) online, CAST(SUM(offline) AS SIGNED) offline, CAST(SUM(unknown) AS SIGNED) unknown, CAST(SUM(orphaned) AS SIGNED) orphaned, CAST(SUM(rx) AS SIGNED) rx, CAST(SUM(tx) AS SIGNED) tx
			FROM stats_hood
			INNER JOIN hoods ON hoods.id = stats_hood.hood
			INNER JOIN hoodsv2 ON hoodsv2.name = hoods.name
			WHERE time > 1531612800
			GROUP BY time
		""")
		statsv1 = mysql.fetchall("""
			SELECT time, CAST(SUM(clients) AS SIGNED) clients, CAST(SUM(online) AS SIGNED) online, CAST(SUM(offline) AS SIGNED) offline, CAST(SUM(unknown) AS SIGNED) unknown, CAST(SUM(orphaned) AS SIGNED) orphaned, CAST(SUM(rx) AS SIGNED) rx, CAST(SUM(tx) AS SIGNED) tx
			FROM stats_hood
			INNER JOIN hoods ON hoods.id = stats_hood.hood
			LEFT JOIN hoodsv1 ON hoodsv1.name = hoods.name
			WHERE time > 1531612800 AND ( hoodsv1.name IS NOT NULL OR hoods.name IN ('ArnsteinV1','MuenchbergV1','MarktredwitzV1','BayreuthV1','AnsbachV1','FichtelbergV1','BambergV1','ForchheimV1','ErlangenV1','ErlangenWestV1','EbernV1','CoburgV1','HassbergeV1','LaufV1','RehauV1','AschaffenburgV1','WuerzburgV1','AdelsdorfV1','EbermannstadtV1','NuernbergV1','HassbergeSuedV1','FuerthV1','SchweinfurtV1','BGLV1') )
			GROUP BY time
		""")
		mysql.close()
		statsv2 = mysql.utcawaretupleint(statsv2,"time")
		statsv1 = mysql.utcawaretupleint(statsv1,"time")

		return render_template("v2routers.html",statsv2 = statsv2,statsv1 = statsv1)
	except Exception as e:
		writelog(CONFIG["debug_dir"] + "/fail_v2.txt", str(e))
		import traceback
		writefulllog("Warning: Failed to display v2 page: %s\n__%s" % (e, traceback.format_exc().replace("\n", "\n__")))


# router by mac (short link version)
@app.route('/mac/<mac>', methods=['GET'])
def router_mac(mac):
	mysql = FreifunkMySQL()
	res_routers = mysql.fetchall("""
		SELECT id
		FROM router
		INNER JOIN router_netif ON router.id = router_netif.router
		WHERE mac = %s
		GROUP BY mac, id
	""",(mac2int(mac),))
	mysql.close()
	if len(res_routers) != 1:
		return redirect(url_for("router_list", q="mac:%s" % mac))
	elif request.args.get('fffconfig', None) != None:
		return redirect(url_for("router_info", dbid=res_routers[0]["id"], fffconfig=1))
	elif request.args.get('json', None) != None:
		return redirect(url_for("router_info", dbid=res_routers[0]["id"], json=1))
	else:
		return redirect(url_for("router_info", dbid=res_routers[0]["id"]))

@app.route('/routers/<dbid>', methods=['GET', 'POST'])
def router_info(dbid):
	try:
		mysql = FreifunkMySQL()
		router = mysql.findone("""
			SELECT router.*, hoods.id AS hoodid, hoods.name AS hoodname FROM router
			INNER JOIN hoods ON router.hood = hoods.id
			WHERE router.id = %s LIMIT 1
		""",(dbid,))
		mac = None
		
		if router:
			if request.args.get('fffconfig', None) != None:
				mysql.close()
				s = "\nconfig fff 'system'\n"
				s += "        option hostname '{}'\n".format(router["hostname"])
				s += "        option description '{}'\n".format(router["description"])
				s += "        option latitude '{}'\n".format(router["lat"] if router["lat"] else "")
				s += "        option longitude '{}'\n".format(router["lng"] if router["lng"] else "")
				s += "        option position_comment '{}'\n".format(router["position_comment"])
				s += "        option contact '{}'\n".format(router["contact"])
				return Response(s,mimetype='text/plain')

			router = mysql.utcaware(router,["created","last_contact"])

			router["user"] = mysql.findone("SELECT nickname FROM users WHERE email = %s",(router["contact"],),"nickname")
			router["netifs"] = mysql.fetchall("""SELECT * FROM router_netif WHERE router = %s""",(dbid,))
			
			netifs = []
			for n in router["netifs"]:
				n["ipv6_addrs"] = mysql.fetchall("""SELECT ipv6 FROM router_ipv6 WHERE router = %s AND netif = %s""",(dbid,n["netif"],),"ipv6")
				if n["netif"]=="br-mesh":
					mac = n["mac"]
				netifs.append(n["netif"])
			
			router["neighbours"] = mysql.fetchall("""
				SELECT nb.mac, nb.netif, nb.quality, r.hostname, r.id
				FROM router_neighbor AS nb
				LEFT JOIN (
					SELECT router, mac FROM router_netif GROUP BY mac, router
					) AS net ON nb.mac = net.mac
				LEFT JOIN router as r ON net.router = r.id
				WHERE nb.router = %s
				ORDER BY nb.quality DESC
			""",(dbid,))
			# FIX SQL: only one from router_netif
			
			router["gws"] = mysql.fetchall("""
				SELECT router_gw.mac AS mac, quality, router_gw.netif AS netif, gw_class, selected, gw.name AS gw, n1.netif AS gwif, n2.netif AS batif, n2.mac AS batmac
				FROM router_gw
				LEFT JOIN (
					gw_netif AS n1
					INNER JOIN gw ON n1.gw = gw.id
					LEFT JOIN gw_netif AS n2 ON n1.mac = n2.vpnmac AND n1.gw = n2.gw
				) ON router_gw.mac = n1.mac
				WHERE router = %s
			""",(dbid,))
			for gw in router["gws"]:
				gw["label"] = gw_name(gw)
				gw["batX"] = gw_bat(gw)
			
			router["events"] = mysql.fetchall("""SELECT * FROM router_events WHERE router = %s""",(dbid,))
			router["events"] = mysql.utcawaretuple(router["events"],"time")
			
			## Create json with all data except stats
			if request.args.get('json', None) != None:
				mysql.close()
				return Response(bson2json(router, sort_keys=True, indent=4), mimetype='application/json')
			
			cwan = "blue"
			cclient = "orange"
			cbatman = "#29c329"
			cvpn = "red"
			chidden = "gray"
			
			## Label netifs AFTER json if clause
			for n in router["netifs"]:
				netif = n["netif"];
				desc = None
				color = None
				if netif == 'br-mesh':
					desc = "Bridge"
				elif netif.endswith('.1'):
					desc = "Clients via Ethernet"
					color = cclient
				elif netif.endswith('.2'):
					desc = "WAN"
					color = cwan
				elif netif.endswith('.3'):
					desc = "Mesh via Ethernet"
					color = cbatman
				elif netif == "w2ap":
					desc = "Clients @ 2.4 GHz"
					color = cclient
				elif netif == "w2mesh" or netif == "w2ibss":
					desc = "Mesh @ 2.4 GHz"
					color = cbatman
				elif netif == "w2configap":
					desc = "Config @ 2.4 GHz"
					color = chidden
				elif netif == "w5ap":
					desc = "Clients @ 5 GHz"
					color = cclient
				elif netif == "w5mesh" or netif == "w5ibss":
					desc = "Mesh @ 5 GHz"
					color = cbatman
				elif netif == "w5configap":
					desc = "Config @ 5 GHz"
					color = chidden
				elif netif == "fffVPN":
					desc = "Fastd VPN Tunnel"
					color = cvpn
				elif netif.startswith("l2tp"):
					desc = "L2TP VPN Tunnel"
					color = cvpn
				elif netif.startswith("bat"):
					desc = "Batman Interface"
				elif netif.startswith("eth") and any(item.startswith("{}.".format(netif)) for item in netifs):
					desc = "Switch"
				elif netif == "eth1":
					# already known from above: no switch; no one-port, as there must be eth0
					if not "eth0" in netifs or any(item.startswith("eth0.") for item in netifs):
						desc = "WAN"
						color = cwan
					else:
						# Second port of Nanostation M2
						desc = "Ethernet Multi-Port"
				elif netif == "eth0":
					if any(item.startswith("eth1.") for item in netifs):
						# already known from above: no switch
						desc = "WAN"
						color = cwan
					else:
						# First port of Nanostation M2 or ONE-Port
						desc = "Ethernet Multi-Port"
				n["description"] = desc
				n["color"] = color

			## Set color for neighbors AFTER json if clause
			for n in router["neighbours"]:
				n["color"] = neighbor_color(n["quality"],n["netif"],router["routing_protocol"])

			router["stats"] = mysql.fetchall("""SELECT * FROM router_stats WHERE router = %s""",(dbid,))
			for s in router["stats"]:
				s["time"] = mysql.utcawareint(s["time"])

			threshold_neighstats = (utcnow() - datetime.timedelta(hours=24)).timestamp()
			neighfetch = mysql.fetchall("""
				SELECT quality, mac, time FROM router_stats_neighbor WHERE router = %s AND time > %s
			""",(dbid,threshold_neighstats,))

			neighdata = {}
			for ns in neighfetch:
				ns["time"] = {"$date": int(mysql.utcawareint(ns["time"]).timestamp()*1000)}
				if not ns["mac"] in neighdata:
					neighdata[ns["mac"]] = []
				neighdata[ns["mac"]].append(ns)

			neighident = mysql.fetchall("""
				SELECT snb.mac, r.hostname, n.netif
				FROM router_stats_neighbor AS snb
				INNER JOIN router_netif AS n ON snb.mac = n.mac
				INNER JOIN router AS r ON n.router = r.id
				WHERE snb.router = %s AND n.netif <> 'w2ap' AND n.netif <> 'w5ap'
				GROUP BY snb.mac, r.hostname, n.netif
			""",(dbid,))
			neighlabel = {}
			for ni in neighident:
				label = ni["hostname"]
				# add network interface when there are multiple links to same node
				for ni2 in neighident:
					if label == ni2["hostname"] and ni["mac"] != ni2["mac"]:
						# This shows the NEIGHBOR'S interface name
						label += "@" + ni["netif"]
				append = " (old)"
				for nnn in router["neighbours"]:
					if nnn["mac"] == ni["mac"]:
						append = ""
				neighlabel[ni["mac"]] = label + append

			gwfetch = mysql.fetchall("""
				SELECT quality, mac, time FROM router_stats_gw WHERE router = %s
			""",(dbid,))
			
			for ns in gwfetch:
				ns["time"] = mysql.utcawareint(ns["time"])

			if request.method == 'POST':
				if request.form.get("act") == "delete":
					# a router may not have a owner, but admin users still can delete it
					if is_authorized(router["user"], session):
						delete_router(mysql,dbid)
						flash("<b>Router <i>%s</i> deleted!</b>" % router["hostname"], "success")
						mysql.close()
						return redirect(url_for("index"))
					else:
						flash("<b>You are not authorized to perform this action!</b>", "danger")
				elif request.form.get("act") == "ban":
					if session.get('admin'):
						if mac:
							ban_router(mysql,dbid)
							delete_router(mysql,dbid)
							flash("<b>Router <i>%s</i> banned!</b>" % router["hostname"], "success")
							mysql.close()
							return redirect(url_for("index"))
						else:
							flash("<b>Router has no br-mesh and thus cannot be banned!</b>", "danger")
					else:
						flash("<b>You are not authorized to perform this action!</b>", "danger")
				elif request.form.get("act") == "changeblocked" and mac:
					if session.get('admin'):
						if request.form.get("blocked") == "true":
							added = mysql.utcnow()
							mysql.execute("INSERT INTO blocked (mac, added) VALUES (%s, %s)",(mac,added,))
							mysql.execute("""
								INSERT INTO router_events (router, time, type, comment)
								VALUES (%s, %s, %s, %s)
							""",(dbid,mysql.utcnow(),"admin","Marked as blocked",))
							mysql.commit()
						else:
							mysql.execute("DELETE FROM blocked WHERE mac = %s",(mac,))
							mysql.execute("""
								INSERT INTO router_events (router, time, type, comment)
								VALUES (%s, %s, %s, %s)
							""",(dbid,mysql.utcnow(),"admin","Removed blocked status",))
							mysql.commit()
						router["events"] = mysql.fetchall("""SELECT * FROM router_events WHERE router = %s""",(dbid,))
						router["events"] = mysql.utcawaretuple(router["events"],"time")
					else:
						flash("<b>You are not authorized to perform this action!</b>", "danger")
				elif request.form.get("act") == "report":
					abusemails = mysql.fetchall("SELECT email FROM users WHERE abuse = 1")
					for a in abusemails:
						send_email(
							recipient = a["email"],
							subject   = "Monitoring: Router %s reported" % router["hostname"],
							content   = "Hello Admin,\n\n" +
									"The router with hostname %s has been reported as abusive by a user.\n" % router["hostname"] +
									"Please take care:\n" +
									"%s\n\n" % url_for("router_info", dbid=dbid, _external=True) +
									"Regards,\nFreifunk Franken Monitoring System"
						)
					flash("<b>Router reported to administrators!</b>", "success")
		else:
			mysql.close()
			return "Router not found"
		
		router["blocked"] = mysql.findone("""
			SELECT blocked.mac
			FROM router_netif AS n
			LEFT JOIN blocked ON n.mac = blocked.mac
			WHERE n.router = %s AND n.netif = 'br-mesh'
		""",(dbid,),"mac")
		mysql.close()
		
		return render_template("router.html",
			router = router,
			mac = mac,
			tileurls = tileurls,
			neighstats = neighdata,
			neighlabel = neighlabel,
			gwstats = gwfetch,
			authuser = is_authorized(router["user"], session),
			authadmin = session.get('admin')
			)
	except Exception as e:
		writelog(CONFIG["debug_dir"] + "/fail_router.txt", str(e))
		import traceback
		writefulllog("Warning: Failed to display router details page: %s\n__%s" % (e, traceback.format_exc().replace("\n", "\n__")))

@app.route('/users')
def user_list():
	mysql = FreifunkMySQL()
	users = mysql.fetchall("SELECT id, nickname, email, created, admin FROM users ORDER BY nickname COLLATE utf8_unicode_ci ASC")
	user_routers = stattools.router_user_sum(mysql)
	mysql.close()
	users = mysql.utcawaretuple(users,"created")
	
	return render_template("user_list.html",
		user_routers = user_routers,
		users = users,
		users_count = len(users)
	)

@app.route('/users/<nickname>', methods=['GET', 'POST'])
def user_info(nickname):
	mysql = FreifunkMySQL()
	user = mysql.findone("SELECT * FROM users WHERE nickname = %s LIMIT 1",(nickname,))
	user["created"] = mysql.utcaware(user["created"])
	if not user:
		mysql.close()
		return "User not found"
	if request.method == 'POST':
		if request.form.get("action") == "changepw":
			if is_authorized(user["nickname"], session):
				if request.form["password"] != request.form["password_rep"]:
					flash("<b>Passwords did not match!</b>", "danger")
				elif request.form["password"] == "":
					flash("<b>Password must not be empty!</b>", "danger")
				else:
					set_user_password(mysql, user["nickname"], request.form["password"])
					flash("<b>Password changed!</b>", "success")
			else:
				flash("<b>You are not authorized to perform this action!</b>", "danger")
		elif request.form.get("action") == "changemail":
			if is_authorized(user["nickname"], session):
				if request.form["email"] != request.form["email_rep"]:
					flash("<b>E-Mail addresses do not match!</b>", "danger")
				elif not "@" in request.form["email"]:
					flash("<b>Invalid E-Mail addresse!</b>", "danger")
				else:
					try:
						set_user_email(mysql, user["nickname"], request.form["email"])
						flash("<b>E-Mail changed!</b>", "success")
						if not session.get('admin'):
							password = base64.b32encode(os.urandom(10)).decode()
							set_user_password(mysql, user["nickname"], password)
							send_email(
								recipient = request.form['email'],
								subject   = "Password for %s" % user['nickname'],
								content   = "Hello %s,\n\n" % user["nickname"] +
											"You changed your email address on https://monitoring.freifunk-franken.de/\n" +
										"To verify your new email address your password was changed to %s\n" % password +
										"... and sent to your new address. Please log in and change it.\n\n" +
										"Regards,\nFreifunk Franken Monitoring System"
							)
							mysql.close()
							return logout()
						else:
							# force db data reload
							user = mysql.findone("SELECT * FROM users WHERE nickname = %s LIMIT 1",(nickname,))
							user["created"] = mysql.utcaware(user["created"])
					except AccountWithEmailExists:
						flash("<b>There is already an account with this E-Mail Address!</b>", "danger")
			else:
				flash("<b>You are not authorized to perform this action!</b>", "danger")
		elif request.form.get("action") == "changeadmin":
			if session.get('admin'):
				set_user_admin(mysql, nickname, request.form.get("admin") == "true")
				# force db data reload
				user = mysql.findone("SELECT * FROM users WHERE nickname = %s LIMIT 1",(nickname,))
				user["created"] = mysql.utcaware(user["created"])
			else:
				flash("<b>You are not authorized to perform this action!</b>", "danger")
		elif request.form.get("action") == "changeabuse":
			if session.get('admin'):
				set_user_abuse(mysql, nickname, request.form.get("abuse") == "true")
				# force db data reload
				user = mysql.findone("SELECT * FROM users WHERE nickname = %s LIMIT 1",(nickname,))
				user["created"] = mysql.utcaware(user["created"])
			else:
				flash("<b>You are not authorized to perform this action!</b>", "danger")
		elif request.form.get("action") == "deleteaccount":
			if is_authorized(user["nickname"], session):
				mysql.execute("DELETE FROM users WHERE nickname = %s LIMIT 1",(nickname,))
				mysql.commit()
				flash("<b>User <i>%s</i> deleted!</b>" % nickname, "success")
				mysql.close()
				if user["nickname"] == session.get("user"):
					session.pop('user', None)
				return redirect(url_for("user_list"))
			else:
				flash("<b>You are not authorized to perform this action!</b>", "danger")
	routers = mysql.fetchall("""
		SELECT router.id, hostname, status, hoods.id AS hoodid, hoods.name AS hood, firmware, hardware, created, sys_uptime, clients, reset, blocked, v2, local
		FROM router
		INNER JOIN hoods ON router.hood = hoods.id
		LEFT JOIN (
			SELECT router, blocked.mac AS blocked FROM router_netif
			INNER JOIN blocked ON router_netif.mac = blocked.mac
			WHERE netif = 'br-mesh'
		) AS b
		ON router.id = b.router
		WHERE contact = %s
		ORDER BY hostname ASC
	""",(user["email"],))
	mysql.close()
	routers = mysql.utcawaretuple(routers,"created")
	return render_template("user.html",
		user=user,
		routers=routers,
		routers_count=len(routers),
		authuser = is_authorized(user["nickname"], session),
		authadmin = session.get('admin')
	)

@app.route('/statistics')
def global_statistics():
	mysql = FreifunkMySQL()
	stats = mysql.fetchall("SELECT * FROM stats_global")
	return helper_statistics(mysql,stats,None,None)

@app.route('/hoodstatistics/<selecthood>')
def global_hoodstatistics(selecthood):
	selecthood = int(selecthood)
	mysql = FreifunkMySQL()
	stats = mysql.fetchall("SELECT * FROM stats_hood WHERE hood = %s",(selecthood,))
	return helper_statistics(mysql,stats,selecthood,None)

@app.route('/gwstatistics/<selectgw>')
def global_gwstatistics(selectgw):
	mysql = FreifunkMySQL()
	stats = mysql.fetchall("SELECT * FROM stats_gw WHERE mac = %s",(mac2int(selectgw),))
	selectgw = shortmac2mac(selectgw)
	return helper_statistics(mysql,stats,None,selectgw)

def helper_statistics(mysql,stats,selecthood,selectgw):
	try:
		hoods = stattools.hoods(mysql,selectgw)
		gws = stattools.gws_ifs(mysql,selecthood)
		
		if selecthood:
			selecthoodname = mysql.findone("SELECT name FROM hoods WHERE id = %s",(selecthood,),'name')
		else:
			selecthoodname = None
		
		if selectgw:
			selectgwint = mac2int(selectgw)
		else:
			selectgwint = None
		
		if selecthood and not selecthoodname:
			mysql.close()
			return "Hood not found"
		if selectgw and not selectgwint in gws:
			mysql.close()
			return "Gateway not found"
		
		stats = mysql.utcawaretupleint(stats,"time")
		
		numnew = len(hoods)-27
		if numnew < 1:
			numnew = 1
		
		if selectgw:
			newest_routers = mysql.fetchall("""
				SELECT router.id, hostname, hoods.id AS hoodid, hoods.name AS hood, created
				FROM router
				INNER JOIN hoods ON router.hood = hoods.id
				INNER JOIN router_gw ON router.id = router_gw.router
				WHERE hardware <> 'Legacy' AND mac = %s
				ORDER BY created DESC
				LIMIT %s
			""",(mac2int(selectgw),numnew,))
		else:
			if selecthood:
				where = " AND hoods.id = %s"
				tup = (selecthood,numnew,)
			else:
				where = ""
				tup = (numnew,)
			newest_routers = mysql.fetchall("""
				SELECT router.id, hostname, hoods.id AS hoodid, hoods.name AS hood, created
				FROM router
				INNER JOIN hoods ON router.hood = hoods.id
				WHERE hardware <> 'Legacy' {}
				ORDER BY created DESC
				LIMIT %s
			""".format(where),tup)
		newest_routers = mysql.utcawaretuple(newest_routers,"created")
		
		clients = stattools.total_clients(mysql)
		router_status = stattools.router_status(mysql)
		router_models = stattools.router_models(mysql,selecthood,selectgw)
		router_firmwares = stattools.router_firmwares(mysql,selecthood,selectgw)
		hoods_sum = stattools.hoods_sum(mysql,selectgw)
		hoods_gws = stattools.hoods_gws(mysql)
		gws_sum = stattools.gws_sum(mysql,selecthood)
		gws_info = stattools.gws_info(mysql,selecthood)
		gws_admin = stattools.gws_admin(mysql,selectgw)
		mysql.close()
		
		return render_template("statistics.html",
			selecthood = selecthood,
			selecthoodname = selecthoodname,
			selectgw = selectgw,
			selectgwint = selectgwint,
			stats = stats,
			clients = clients,
			router_status = router_status,
			router_models = router_models,
			router_firmwares = router_firmwares,
			hoods = hoods,
			hoods_sum = hoods_sum,
			hoods_gws = hoods_gws,
			newest_routers = newest_routers,
			gws = gws,
			gws_sum = gws_sum,
			gws_info = gws_info,
			gws_admin = gws_admin
		)
	except Exception as e:
		writelog(CONFIG["debug_dir"] + "/fail_stats.txt", str(e))
		import traceback
		writefulllog("Warning: Failed to display stats page: %s\n__%s" % (e, traceback.format_exc().replace("\n", "\n__")))

@app.route('/gateways')
def gateways():
	try:
		mysql = FreifunkMySQL()
		gws = stattools.gateways(mysql)
		ipv4 = stattools.gws_ipv4(mysql)
		ipv6 = stattools.gws_ipv6(mysql)
		dhcp = stattools.gws_dhcp(mysql)
		mysql.close()
		
		return render_template("gws.html",
			gws = gws,
			ipv4 = ipv4,
			ipv6 = ipv6,
			dhcp = dhcp
		)
	except Exception as e:
		writelog(CONFIG["debug_dir"] + "/fail_gateways.txt", str(e))
		import traceback
		writefulllog("Warning: Failed to display gateways page: %s\n__%s" % (e, traceback.format_exc().replace("\n", "\n__")))

@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		try:
			password = base64.b32encode(os.urandom(10)).decode()
			register_user(request.form['user'], request.form['email'], password)
			send_email(
				recipient = request.form['email'],
				subject   = "Password for %s" % request.form['user'],
				content   = "Hello %s,\n\n" % request.form['user'] +
						"You created an account on https://monitoring.freifunk-franken.de/\n" +
						"To verify your new email address your password was autogenerated to %s\n" % password +
						"... and sent to your address. Please log in and change it.\n\n" +
						"Regards,\nFreifunk Franken Monitoring System"
			)
			flash("<b>Registration successful!</b> - Your password was sent to %s" % request.form['email'], "success")
		except AccountWithEmailExists:
			flash("<b>There is already an account with this E-Mail Address!</b>", "danger")
		except AccountWithNicknameExists:
			flash("<b>There is already an active account with this Nickname!</b>", "danger")
		except AccountWithEmptyField:
			flash("<b>Please fill all fields!</b>", "danger")
	return render_template("register.html")

@app.route('/resetpw', methods=['GET', 'POST'])
def resetpw():
	try:
		if request.method == 'POST':
			token = base64.b32encode(os.urandom(10)).decode()
			mysql = FreifunkMySQL()
			user = reset_user_password(mysql, request.form['email'], token)
			mysql.close()
			send_email(
				recipient = request.form['email'],
				subject   = "Password reset link",
				content   = "Hello %s,\n\n" % user["nickname"] +
							"You attemped to reset your password on https://monitoring.freifunk-franken.de/\n" +
							"To verify you a reset link was sent to you:\n" +
							"%s\n" % url_for('resetpw', email=request.form['email'], token=token, _external=True) +
							"Clicking this link will reset your password and send the new password to your email address.\n\n" +
							"Regards,\nFreifunk Franken Monitoring System"
			)
			flash("<b>A password reset link was sent to %s</b>" % request.form['email'], "success")
		elif "token" in request.args:
			password = base64.b32encode(os.urandom(10)).decode()
			mysql = FreifunkMySQL()
			user = reset_user_password(mysql, request.args['email'], request.args['token'], password)
			mysql.close()
			send_email(
				recipient = request.args['email'],
				subject   = "Your new Password",
				content   = "Hello %s,\n\n" % user["nickname"] +
							"You attemped to reset your password on https://monitoring.freifunk-franken.de/\n" +
							"Your new Password: %s\n" % password +
							"Please log in and change it\n\n" +
							"Regards,\nFreifunk Franken Monitoring System"
			)
			flash("<b>Password reset successful!</b> - Your password was sent to %s" % request.args['email'], "success")
	except AccountNotExisting:
		flash("<b>No Account found with this E-Mail address!</b>", "danger")
	except InvalidToken:
		flash("<b>Invalid password token!</b>", "danger")
	return render_template("resetpw.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		referrer = request.form["referrer"]
		user_login = check_login_details(request.form["user"], request.form["password"])
		if user_login:
			session['user'] = user_login["nickname"]
			session['admin'] = user_login.get("admin", False)
			return redirect(referrer)
		else:
			flash("<b>Invalid login details!</b>", "danger")
	else:
		referrer = request.referrer or url_for("index")
	return render_template("login.html", referrer=referrer)

@app.route('/logout')
def logout():
	session.pop('user', None)
	session.pop('admin', None)
	return redirect(request.referrer or url_for("index"))


@app.context_processor
def register_helpers():
	return {
		"is_authorized_for": lambda owner: is_authorized(owner, session)
	}


if not os.path.isfile("/var/lib/ffmap/secret_key"):
	open("/var/lib/ffmap/secret_key", "wb").write(os.urandom(24))
	os.chmod("/var/lib/ffmap/secret_key", 0o600)

app.secret_key = open("/var/lib/ffmap/secret_key", "rb").read()

if __name__ == '__main__':
	app.run(host='0.0.0.0', debug=True)
else:
	app.template_folder = "/usr/share/ffmap/templates"
	app.static_folder = "/usr/share/ffmap/static"
	#app.debug = True
