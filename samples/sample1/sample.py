import sqlite3
import requests

def setup_db():
 con = sqlite3.connect(":memory:")
 cur = con.cursor()
 cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
 cur.executemany(
 "INSERT INTO users (username, password) VALUES (?, ?)",
 [("alice", "s3cret"), ("bob", "hunter2")]
 )
 con.commit()
 return con

def login(con, username, password):
 cur = con.cursor()
 # Consulta usuarios
 sql_query = f"SELECT id FROM users WHERE username = '{username}' AND password = '{password}'"
 cur.execute(
 sql_query
 )
 return cur.fetchone()

def new_login(con, username, password):
 cur = con.cursor()
 # Consulta usuarios
 cur.execute(
 "SELECT id FROM users WHERE username = ? AND password = ?",
 (username, password)
 )
 return cur.fetchone()

def check_username(username):
 response = requests.get(f"https://api.github.com/users/{username}")
 return response

def is_online_username(username):
 import os
 os.system(f"touch /tmp/{username}")

def demo():
 con = setup_db()

 username = input("Username: ")
 password = input("Password: ")
 ok = login(con, username, password)
 print("Login:", bool(ok))
 ok = new_login(con, username, password)
 print("New Login:", bool(ok))
 response = check_username(username)
 print("Check username:", response.status_code) # 200

if __name__ == "__main__":
  demo()