#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.dbtools import FreifunkDB
from ffmap.misc import *

from werkzeug.security import generate_password_hash, check_password_hash

db = FreifunkDB().handle()

class AccountWithEmailExists(Exception):
	pass

class AccountWithNicknameExists(Exception):
	pass

class AccountNotExisting(Exception):
	pass

class InvalidToken(Exception):
	pass

def register_user(nickname, email, password):
	user_with_nick  = db.users.find_one({"nickname": nickname})
	user_with_email = db.users.find_one({"email": email})
	if user_with_email:
		raise AccountWithEmailExists()
	elif user_with_nick and "email" in user_with_nick:
		raise AccountWithNicknameExists()
	else:
		user_update = {
			"nickname": nickname,
			"password": generate_password_hash(password),
			"email": email,
			"created": utcnow()
		}
		if user_with_nick:
			db.users.update_one({"_id": user_with_nick["_id"]}, {"$set": user_update})
			return user_with_nick["_id"]
		else:
			return db.users.insert_one(user_update).inserted_id

def check_login_details(nickname, password):
	user = db.users.find_one({"nickname": nickname})
	if user and check_password_hash(user.get('password', ''), password):
		return user
	else:
		return False

def reset_user_password(email, token=None, password=None):
	user = db.users.find_one({"email": email})
	if not user:
		raise AccountNotExisting()
	elif password:
		if user.get("token") == token:
			db.users.update_one({"_id": user["_id"]}, {
				"$set": {"password": generate_password_hash(password)},
				"$unset": {"token": 1},
			})
		else:
			raise InvalidToken()
	elif token:
		db.users.update_one({"_id": user["_id"]}, {"$set": {"token": token}})

def set_user_password(nickname, password):
	user = db.users.find_one({"nickname": nickname})
	if not user:
		raise AccountNotExisting()
	elif password:
		db.users.update_one({"_id": user["_id"]}, {
			"$set": {"password": generate_password_hash(password)},
		})

def set_user_email(nickname, email):
	user = db.users.find_one({"nickname": nickname})
	user_with_email = db.users.find_one({"email": email})
	if user_with_email:
		raise AccountWithEmailExists()
	if not user:
		raise AccountNotExisting()
	elif email:
		db.users.update_one({"_id": user["_id"]}, {
			"$set": {"email": email},
		})

def set_user_admin(nickname, admin):
	db.users.update({"nickname": nickname}, {"$set": {"admin": admin}})
