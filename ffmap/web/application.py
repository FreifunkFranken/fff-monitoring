#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))

from ffmap.web.api import api
from ffmap.web.filters import filters
from ffmap.dbtools import FreifunkDB
from ffmap import stattools
from ffmap.usertools import *
from ffmap.web.helpers import *

from flask import Flask, render_template, request, Response, redirect, url_for, flash, session
import bson
import pymongo
from bson.json_util import dumps as bson2json
from bson.objectid import ObjectId
import base64

app = Flask(__name__)
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(filters)

db = FreifunkDB().handle()

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
	return render_template("router_list.html", query_str=query_str, routers=db.routers.find(query, {
		"hostname": 1,
		"status": 1,
		"hood": 1,
		"user.nickname": 1,
		"hardware.name": 1,
		"created": 1,
		"system.uptime": 1,
		"system.clients": 1,
	}).sort("hostname", pymongo.ASCENDING))

@app.route('/routers/<dbid>', methods=['GET', 'POST'])
def router_info(dbid):
	try:
		router = db.routers.find_one({"_id": ObjectId(dbid)})
		assert router
		if request.method == 'POST':
			if request.form.get("act") == "delete":
				user = None
				# a router may not have a owner, but admin users still can delete it
				if ("user" in router) and ("nickname" in router["user"]):
					user = router["user"]["nickname"]
				if is_authorized(user, session):
					db.routers.delete_one({"_id": ObjectId(dbid)})
					flash("<b>Router <i>%s</i> deleted!</b>" % router["hostname"], "success")
					return redirect(url_for("index"))
				else:
					flash("<b>You are not authorized to perform this action!</b>", "danger")
	except (bson.errors.InvalidId, AssertionError):
		return "Router not found"
	if request.args.get('json', None) != None:
		del router["stats"]
		#FIXME: Only as admin
		return Response(bson2json(router, sort_keys=True, indent=4), mimetype='application/json')
	else:
		return render_template("router.html", router=router, tileurls=tileurls)

@app.route('/users')
def user_list():
	return render_template("user_list.html",
		user_routers = stattools.router_user_sum(),
		users = db.users.find({}, {"nickname": 1, "email": 1, "created": 1, "admin": 1}).sort("nickname", pymongo.ASCENDING)
	)

@app.route('/users/<nickname>', methods=['GET', 'POST'])
def user_info(nickname):
	try:
		user = db.users.find_one({"nickname": nickname})
		assert user
	except AssertionError:
		return "User not found"
	if request.method == 'POST':
		if is_authorized(user["nickname"], session):
			if request.form.get("action") == "changepw":
				if request.form["password"] != request.form["password_rep"]:
					flash("<b>Passwords did not match!</b>", "danger")
				elif request.form["password"] == "":
					flash("<b>Password must not be empty!</b>", "danger")
				else:
					set_user_password(user["nickname"], request.form["password"])
					flash("<b>Password changed!</b>", "success")
			elif request.form.get("action") == "changemail":
				if request.form["email"] != request.form["email_rep"]:
					flash("<b>E-Mail addresses do not match!</b>", "danger")
				elif not "@" in request.form["email"]:
					flash("<b>Invalid E-Mail addresse!</b>", "danger")
				else:
					try:
						set_user_email(user["nickname"], request.form["email"])
						flash("<b>E-Mail changed!</b>", "success")
						if not session.get('admin'):
							password = base64.b32encode(os.urandom(10)).decode()
							set_user_password(user["nickname"], password)
							send_email(
								recipient = request.form['email'],
								subject   = "Password for %s" % user['nickname'],
								content   = "Hello %s,\n\n" % user["nickname"] +
								            "You changed your email address on https://monitoring.freifunk-franken.de/\n" +
									    "To verify your new email address your password was changed to %s\n" % password +
									    "... and sent to your new address. Please log in and change it.\n\n" +
									    "Regards,\nFreifunk Franken Monitoring System"
							)
							return logout()
						else:
							# force db data reload
							user = db.users.find_one({"nickname": nickname})
					except AccountWithEmailExists:
						flash("<b>There is already an account with this E-Mail Address!</b>", "danger")
			elif request.form.get("action") == "changeadmin":
				if session.get('admin'):
					set_user_admin(nickname, request.form.get("admin") == "true")
					# force db data reload
					user = db.users.find_one({"nickname": nickname})
			elif request.form.get("action") == "deleteaccount":
				if session.get('admin'):
					db.users.delete_one({"nickname": nickname})
					flash("<b>User <i>%s</i> deleted!</b>" % nickname, "success")
					return redirect(url_for("user_list"))
		else:
			flash("<b>You are not authorized to perform this action!</b>", "danger")
	routers=db.routers.find({"user._id": user["_id"]}, {
		"hostname": 1,
		"status": 1,
		"hood": 1,
		"software.firmware": 1,
		"hardware.name": 1,
		"created": 1,
		"system.uptime": 1,
		"system.clients": 1,
	}).sort("hostname", pymongo.ASCENDING)
	return render_template("user.html", user=user, routers=routers)

@app.route('/statistics')
def global_statistics():
	hoods = stattools.hoods()
	return render_template("statistics.html",
		selecthood = "All Hoods",
		stats = db.stats.find({}, {"_id": 0}),
		clients = stattools.total_clients(),
		router_status = stattools.router_status(),
		router_models = stattools.router_models(),
		router_firmwares = stattools.router_firmwares(),
		hoods = hoods,
		hoods_sum = stattools.hoods_sum(),
		newest_routers = db.routers.find({"hardware.name": {"$ne": "Legacy"}}, {"hostname": 1, "hood": 1, "created": 1}).sort("created", pymongo.DESCENDING).limit(len(hoods)+1)
	)

@app.route('/hoodstatistics/<selecthood>')
def global_hoodstatistics(selecthood):
	hoods = stattools.hoods()
	return render_template("statistics.html",
		selecthood = selecthood,
		stats = db.hoodstats.find({"hood": selecthood}, {"_id": 0, "hood": 0}),
		clients = stattools.total_clients(),
		router_status = stattools.router_status(),
		router_models = stattools.router_models_hood(selecthood),
		router_firmwares = stattools.router_firmwares_hood(selecthood),
		hoods = hoods,
		hoods_sum = stattools.hoods_sum(),
		newest_routers = db.routers.find({"hardware.name": {"$ne": "Legacy"},"hood": selecthood}, {"hostname": 1, "hood": 1, "created": 1}).sort("created", pymongo.DESCENDING).limit(len(hoods)+1)
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
			user = db.users.find_one({"email": request.form['email']})
			reset_user_password(request.form['email'], token)
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
			reset_user_password(request.args['email'], request.args['token'], password)
			user = db.users.find_one({"email": request.args['email']})
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
