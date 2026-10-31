import os, sqlite3
from pathlib import Path

def connect():
    directory=Path(os.environ.get('BIOLENS_CLOUD_DATA','/var/lib/biolens'))
    directory.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(directory/'cloud.sqlite3',timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA foreign_keys=ON')
    return db

def init():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),name TEXT NOT NULL,created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY,project_id TEXT REFERENCES projects(id),user_id TEXT REFERENCES users(id),title TEXT NOT NULL,created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages(seq INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,chat_id TEXT REFERENCES chats(id),user_id TEXT REFERENCES users(id),role TEXT NOT NULL,content TEXT NOT NULL,created TEXT NOT NULL);
        ''')

def rows(sql,args=()):
    with connect() as db:return [dict(r) for r in db.execute(sql,args)]

def execute(sql,args=()):
    with connect() as db:db.execute(sql,args)
