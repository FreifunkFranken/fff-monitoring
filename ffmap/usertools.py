#!/usr/bin/python3

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

from ffmap.mysqltools import FreifunkMySQL
from ffmap.misc import *

from werkzeug.security import generate_password_hash, check_password_hash

class AccountWithEmailExists(Exception):
	pass

class AccountWithNicknameExists(Exception):
	pass

class AccountNotExisting(Exception):
	pass

class InvalidToken(Exception):
	pass

def register_user(nickname, email, password):
	mysql = FreifunkMySQL()

	user_with_nick  = mysql.findone("SELECT id, email FROM users WHERE nickname = %s LIMIT 1",(nickname,))
	user_with_email  = mysql.findone("SELECT id FROM users WHERE email = %s LIMIT 1",(email,),"id")
	pw = generate_password_hash(password)
	if user_with_email:
		mysql.close()
		raise AccountWithEmailExists()
	elif user_with_nick and user_with_nick["email"]:
		mysql.close()
		raise AccountWithNicknameExists()
	else:
		time = mysql.utcnow()
		if user_with_nick:
			mysql.execute("""
				UPDATE users
				SET password = %s, email = %s, created = %s, token = NULL
				WHERE id = %s
				LIMIT 1
			""",(pw,email,time,user_with_nick["id"],))
			mysql.commit()
			mysql.close()
			return user_with_nick["id"]
		else:
			mysql.execute("""
				INSERT INTO users (nickname, password, email, created, token)
				VALUES (%s, %s, %s, %s, NULL)
			""",(nickname,pw,email,time,))
			userid = mysql.cursor().lastrowid
			mysql.commit()
			mysql.close()
			return userid

def check_login_details(nickname, password):
	mysql = FreifunkMySQL()
	
	user  = mysql.findone("SELECT * FROM users WHERE nickname = %s LIMIT 1",(nickname,))
	mysql.close()
	if user and check_password_hash(user.get('password', ''), password):
		return user
	else:
		return False

def reset_user_password(mysql, email, token=None, password=None):
	userid = mysql.findone("SELECT id FROM users WHERE email = %s LIMIT 1",(email,),"id")
	if not user:
		raise AccountNotExisting()
	elif password:
		if user.get("token") == token:
			mysql.execute("""
				UPDATE users
				SET password = %s, token = NULL
				WHERE id = %s
				LIMIT 1
			""",(generate_password_hash(password),userid,))
			mysql.commit()
		else:
			raise InvalidToken()
	elif token:
		mysql.execute("""
			UPDATE users
			SET token = %s
			WHERE id = %s
			LIMIT 1
		""",(token,userid,))
		mysql.commit()

def set_user_password(mysql, nickname, password):
	userid = mysql.findone("SELECT id FROM users WHERE nickname = %s LIMIT 1",(nickname,),"id")
	if not userid:
		raise AccountNotExisting()
	elif password:
		mysql.execute("""
			UPDATE users
			SET password = %s
			WHERE id = %s
			LIMIT 1
		""",(generate_password_hash(password),userid,))
		mysql.commit()

def set_user_email(mysql, nickname, email):
	userid = mysql.findone("SELECT id FROM users WHERE nickname = %s LIMIT 1",(nickname,),"id")
	useridemail = mysql.findone("SELECT id FROM users WHERE email = %s LIMIT 1",(email,),"id")
	if useridemail:
		raise AccountWithEmailExists()
	if not userid:
		raise AccountNotExisting()
	elif email:
		mysql.execute("""
			UPDATE users
			SET email = %s
			WHERE id = %s
			LIMIT 1
		""",(email,userid,))
		mysql.commit()

def set_user_admin(mysql, nickname, admin):
	mysql.execute("""
		UPDATE users
		SET admin = %s
		WHERE nickname = %s
		LIMIT 1
	""",(admin,nickname,))
	mysql.commit()
