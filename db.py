import sqlite3, json, time
from config import DB_PATH

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS batches(
            id INTEGER PRIMARY KEY AUTOINCREMENT, created REAL, status TEXT, items TEXT);
        CREATE TABLE IF NOT EXISTS drafts(
            token TEXT PRIMARY KEY, batch_id INTEGER, item TEXT, text TEXT,
            status TEXT, created REAL, post_urn TEXT);
        CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
        """)

def new_batch(items):
    with conn() as c:
        cur = c.execute("INSERT INTO batches(created,status,items) VALUES(?,?,?)",
                        (time.time(), "sent", json.dumps(items)))
        return cur.lastrowid

def latest_batch():
    with conn() as c:
        r = c.execute("SELECT * FROM batches ORDER BY id DESC LIMIT 1").fetchone()
    if not r: return None
    d = dict(r); d["items"] = json.loads(d["items"]); return d

def batch_status(bid):
    with conn() as c:
        return c.execute("SELECT status FROM batches WHERE id=?", (bid,)).fetchone()["status"]

def set_batch_status(bid, status):
    with conn() as c:
        c.execute("UPDATE batches SET status=? WHERE id=?", (status, bid))

def new_draft(token, batch_id, item, text):
    with conn() as c:
        c.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,NULL)",
                  (token, batch_id, json.dumps(item), text, "pending", time.time()))

def get_draft(token):
    with conn() as c:
        r = c.execute("SELECT * FROM drafts WHERE token=?", (token,)).fetchone()
    if not r: return None
    d = dict(r); d["item"] = json.loads(d["item"]); return d

def update_draft(token, **fields):
    keys = ", ".join(f"{k}=?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE drafts SET {keys} WHERE token=?", (*fields.values(), token))

def kv_set(k, v):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO kv VALUES(?,?)", (k, json.dumps(v)))

def kv_get(k):
    with conn() as c:
        r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return json.loads(r["v"]) if r else None