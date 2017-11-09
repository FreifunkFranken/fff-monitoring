#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.web.api import api
from ffmap.web.filters import filters
from ffmap.mysqltools import FreifunkMySQL
from ffmap import stattools
from ffmap.usertools import *
from ffmap.routertools import delete_router
from ffmap.web.helpers import *

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
	"links_and_routers": "/tiles/links_and_routers",
	"hoods": "/tiles/hoods",
	"hoodsv2": "/tiles/hoodsv2",
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
	query, query_str = parse_router_list_search_query(request.args)
	where, tuple = query2where(query)
	mysql = FreifunkMySQL()
	
	routers = mysql.fetchall("""
		SELECT router.id, hostname, status, hood, contact, nickname, hardware, router.created, sys_uptime, clients
		FROM router
		LEFT JOIN users ON router.contact = users.email
		{}
		ORDER BY hostname ASC
	""".format(where),tuple)
	mysql.close()
	mysql.utcawaretuple(routers,"created")
	
	return render_template("router_list.html", query_str=query_str, routers=routers, numrouters=len(routers))

@app.route('/routers/<dbid>', methods=['GET', 'POST'])
def router_info(dbid):
	try:
		mysql = FreifunkMySQL()
		router = mysql.findone("""SELECT * FROM router WHERE id = %s LIMIT 1""",(dbid,))
		
		if router:
			mysql.utcaware(router,["created","last_contact"])

			router["user"] = mysql.findone("SELECT nickname FROM users WHERE email = %s",(router["contact"],),"nickname")
			router["netifs"] = mysql.fetchall("""SELECT * FROM router_netif WHERE router = %s""",(dbid,))
			for n in router["netifs"]:
				n["ipv6_addrs"] = mysql.fetchall("""SELECT ipv6 FROM router_ipv6 WHERE router = %s AND netif = %s""",(dbid,n["netif"],),"ipv6")
			
			router["neighbours"] = mysql.fetchall("""
				SELECT nb.mac, nb.quality, nb.net_if, r.hostname, r.id
				FROM router_neighbor AS nb
				INNER JOIN (
					SELECT router, mac FROM router_netif GROUP BY mac, router
					) AS net ON nb.mac = net.mac
				INNER JOIN router as r ON net.router = r.id
				WHERE nb.router = %s""",(dbid,))
			# FIX SQL: only one from router_netif
			
			router["events"] = mysql.fetchall("""SELECT * FROM router_events WHERE router = %s""",(dbid,))
			mysql.utcawaretuple(router["events"],"time")
			
			router["stats"] = mysql.fetchall("""SELECT * FROM router_stats WHERE router = %s""",(dbid,))
			for s in router["stats"]:
				s["netifs"] = mysql.fetchdict("""
					SELECT netif, rx, tx FROM router_stats_netif WHERE router = %s AND time = %s
				""",(dbid,s["time"],),"netif")
				s["neighbours"] = mysql.fetchdict("""
					SELECT quality, mac FROM router_stats_neighbor WHERE router = %s AND time = %s
				""",(dbid,s["time"],),"mac","quality")
				#s["neighbours"] = mysql.fetchdict("""
				#	SELECT nb.mac, nb.quality, r.hostname, r.id
				#	FROM router_stats_neighbor AS nb
				#	INNER JOIN (
				#		SELECT router, mac FROM router_netif GROUP BY mac, router
				#		) AS net ON nb.mac = net.mac
				#	INNER JOIN router as r ON net.router = r.id
				#	WHERE nb.router = %s AND time = %s""",(dbid,s["time"],),"mac")
				mysql.utcaware(s["time"])

			if request.method == 'POST':
				if request.form.get("act") == "delete":
					user = None
					# a router may not have a owner, but admin users still can delete it
					if ("user" in router):
						user = router["user"]
					if is_authorized(user, session):
					#if True:
						delete_router(mysql,dbid)
						flash("<b>Router <i>%s</i> deleted!</b>" % router["hostname"], "success")
						mysql.close()
						return redirect(url_for("index"))
					else:
						flash("<b>You are not authorized to perform this action!</b>", "danger")
			mysql.close()
		else:
			mysql.close()
			return "Router not found"
		
		if request.args.get('json', None) != None:
			del router["stats"]
			#FIXME: Only as admin
			return Response(bson2json(router, sort_keys=True, indent=4), mimetype='application/json')
		else:
			return render_template("router.html", router=router, tileurls=tileurls)
	except Exception as e:     # most generic exception you can catch
		logf = open("/data/fff/fail3.txt", "a")
		logf.write("{}\n".format(str(e)))
		logf.close()

@app.route('/users')
def user_list():
	mysql = FreifunkMySQL()
	users = mysql.fetchall("SELECT id, nickname, email, created, admin FROM users ORDER BY nickname ASC")
	user_routers = stattools.router_user_sum(mysql)
	mysql.close()
	mysql.utcawaretuple(users,"created")
	
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
	try:
		if request.method == 'POST':
			if is_authorized(user["nickname"], session):
				if request.form.get("action") == "changepw":
					if request.form["password"] != request.form["password_rep"]:
						flash("<b>Passwords did not match!</b>", "danger")
					elif request.form["password"] == "":
						flash("<b>Password must not be empty!</b>", "danger")
					else:
						set_user_password(mysql, user["nickname"], request.form["password"])
						flash("<b>Password changed!</b>", "success")
				elif request.form.get("action") == "changemail":
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
								mysql.findone("SELECT * FROM users WHERE nickname = %s LIMIT 1",(nickname,))
						except AccountWithEmailExists:
							flash("<b>There is already an account with this E-Mail Address!</b>", "danger")
				elif request.form.get("action") == "changeadmin":
					if session.get('admin'):
						set_user_admin(mysql, nickname, request.form.get("admin") == "true")
						# force db data reload
						mysql.findone("SELECT * FROM users WHERE nickname = %s LIMIT 1",(nickname,))
				elif request.form.get("action") == "deleteaccount":
					if session.get('admin'):
						cur.execute("DELETE FROM users WHERE nickname = %s LIMIT 1",(nickname,))
						mysql.commit()
						flash("<b>User <i>%s</i> deleted!</b>" % nickname, "success")
						mysql.close()
						return redirect(url_for("user_list"))
			else:
				flash("<b>You are not authorized to perform this action!</b>", "danger")
		routers = mysql.fetchall("""
			SELECT id, hostname, status, hood, firmware, hardware, created, sys_uptime, clients
			FROM router
			WHERE contact = %s
			ORDER BY hostname ASC
		""",(user["email"],))
		mysql.close()
		mysql.utcawaretuple(routers,"created")
		return render_template("user.html", user=user, routers=routers, routers_count=len(routers))
	except Exception as e:
		logf = open("/data/fff/fail626.txt", "a")
		logf.write("{}\n".format(str(e)))
		logf.close()
		mysql.close()

@app.route('/statistics')
def global_statistics():
	mysql = FreifunkMySQL()
	hoods = stattools.hoods(mysql)
	
	stats = mysql.fetchall("SELECT * FROM stats_global")
	mysql.utcawaretuple(stats,"time")
	
	newest_routers = mysql.fetchall("""
		SELECT id, hostname, hood, created
		FROM router
		WHERE hardware <> 'Legacy'
		ORDER BY created DESC
		LIMIT %s
	""",(len(hoods)+1,))
	mysql.utcawaretuple(newest_routers,"created")
	
	clients = stattools.total_clients(mysql)
	router_status = stattools.router_status(mysql)
	router_models = stattools.router_models(mysql)
	router_firmwares = stattools.router_firmwares(mysql)
	hoods_sum = stattools.hoods_sum(mysql)
	mysql.close()
	
	return render_template("statistics.html",
		selecthood = "All Hoods",
		stats = stats,
		clients = clients,
		router_status = router_status,
		router_models = router_models,
		router_firmwares = router_firmwares,
		hoods = hoods,
		hoods_sum = hoods_sum,
		newest_routers = newest_routers
	)

@app.route('/hoodstatistics/<selecthood>')
def global_hoodstatistics(selecthood):
	mysql = FreifunkMySQL()
	hoods = stattools.hoods(mysql)
	
	stats = mysql.fetchall("SELECT * FROM stats_hood WHERE hood = %s",(selecthood,))
	mysql.utcawaretuple(stats,"time")
	
	newest_routers = mysql.fetchall("""
		SELECT id, hostname, hood, created
		FROM router
		WHERE hardware <> 'Legacy' AND hood = %s
		ORDER BY created DESC
		LIMIT %s
	""",(selecthood,len(hoods)+1,))
	mysql.utcawaretuple(newest_routers,"created")
	
	clients = stattools.total_clients(mysql)
	router_status = stattools.router_status(mysql)
	router_models = stattools.router_models(mysql,selecthood)
	router_firmwares = stattools.router_firmwares(mysql,selecthood)
	hoods_sum = stattools.hoods_sum(mysql)
	mysql.close()
	
	return render_template("statistics.html",
		selecthood = selecthood,
		stats = stats,
		clients = clients,
		router_status = router_status,
		router_models = router_models,
		router_firmwares = router_firmwares,
		hoods = hoods,
		hoods_sum = hoods_sum,
		newest_routers = newest_routers
	)

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
	return render_template("register.html")

@app.route('/resetpw', methods=['GET', 'POST'])
def resetpw():
	try:
		if request.method == 'POST':
			token = base64.b32encode(os.urandom(10)).decode()
			mysql = FreifunkMySQL()
			user = mysql.findone("SELECT nickname FROM users WHERE email = %s",(request.form['email'],))
			reset_user_password(mysql, request.form['email'], token)
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
			mysql.close()
		elif "token" in request.args:
			password = base64.b32encode(os.urandom(10)).decode()
			mysql = FreifunkMySQL()
			reset_user_password(mysql, request.args['email'], request.args['token'], password)
			user = mysql.findone("SELECT nickname FROM users WHERE email = %s",(request.args['email'],))
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
			mysql.close()
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
