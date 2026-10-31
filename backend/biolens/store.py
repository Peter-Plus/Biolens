import json
import sqlite3
import uuid
from contextvars import ContextVar
user_scope = ContextVar("local_user", default="")
from datetime import datetime, timezone
from .config import DATA_DIR


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


def connect():
    user=user_scope.get()
    directory=DATA_DIR / "accounts" / user if user else DATA_DIR
    directory.mkdir(parents=True,exist_ok=True)
    db = sqlite3.connect(directory / "biolens.sqlite3", timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init(reset_runs=True):
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS outbox(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,name TEXT,path TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY,project_id TEXT,title TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,chat_id TEXT,role TEXT,content TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,chat_id TEXT,request TEXT,status TEXT,created TEXT);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT,kind TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,chat_id TEXT,run_id TEXT,name TEXT,path TEXT,kind TEXT,created TEXT);
        ''')
        if reset_runs:db.execute("UPDATE runs SET status='interrupted' WHERE status='running'")


def rows(sql, args=()):
    with connect() as db:
        return [dict(x) for x in db.execute(sql, args).fetchall()]


def execute(sql, args=()):
    with connect() as db:
        db.execute(sql, args)


def message(chat_id, role, content):
    item={"id":uid(),"chat_id":chat_id,"role":role,"content":content,"created":now()}
    with connect() as db:
        db.execute("INSERT INTO messages VALUES (?,?,?,?,?)",tuple(item.values()))
        if user_scope.get():db.execute("INSERT INTO outbox VALUES(?,?)",(item["id"],json.dumps(item,ensure_ascii=False)))


def event(run_id, kind, payload):
    execute("INSERT INTO events(run_id,kind,payload) VALUES(?,?,?)", (run_id, kind, json.dumps(payload, ensure_ascii=False)))


def artifact(chat_id, run_id, path, kind):
    item = {"id": uid(), "chat_id": chat_id, "run_id": run_id, "name": path.name, "path": str(path), "kind": kind, "created": now()}
    execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?)", tuple(item.values()))
    return {k: v for k, v in item.items() if k != "path"}
