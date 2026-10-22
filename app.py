import os, secrets, time
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE = Path(__file__).parent
DATABASE_URL = os.getenv("DATABASE_URL", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL غير مضبوط في متغيرات البيئة")

app = FastAPI(title="DARK VIP License Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@contextmanager
def conn():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None) as c:
        yield c

with conn() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS licenses(
        key TEXT PRIMARY KEY,
        duration BIGINT NOT NULL,
        expires_at BIGINT,
        hwid TEXT,
        active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at BIGINT NOT NULL)""")

def admin(x_admin_token: str = Header(default="")):
    ok = ADMIN_TOKEN and secrets.compare_digest(x_admin_token.encode(), ADMIN_TOKEN.encode())
    if not ok:
        raise HTTPException(401, "غير مصرح لك بالدخول")

def status_of(r, now):
    if not r["active"]: return "disabled"
    if r["expires_at"] is None: return "unused"
    return "expired" if r["expires_at"] <= now else "active"

@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True, "status": "DARK VIP SERVER IS RUNNING"}

class Validate(BaseModel):
    key: str
    hwid: str

@app.post("/api/validate")
def validate(b: Validate):
    now = int(time.time())
    with conn() as c:
        r = c.execute("SELECT * FROM licenses WHERE key=%s", (b.key.strip().upper(),)).fetchone()
        if not r or not r["active"]:
            return {"valid": False, "reason": "invalid"}
        if r["hwid"] and r["hwid"] != b.hwid:
            return {"valid": False, "reason": "hwid_mismatch"}
        exp = r["expires_at"]
        if exp is None:
            exp = now + r["duration"]
            c.execute("UPDATE licenses SET expires_at=%s, hwid=%s WHERE key=%s", (exp, b.hwid, r["key"]))
        elif exp <= now:
            return {"valid": False, "reason": "expired"}
        elif not r["hwid"]:
            c.execute("UPDATE licenses SET hwid=%s WHERE key=%s", (b.hwid, r["key"]))
    return {"valid": True, "expires_at": exp, "message": "DARK VIP ACTIVATED"}

class Gen(BaseModel):
    duration: int = Field(ge=60, le=315360000)
    quantity: int = Field(ge=1, le=100)

class Ext(BaseModel):
    seconds: int = Field(86400, ge=60, le=31536000)

def new_key():
    a = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "-".join("".join(secrets.choice(a) for _ in range(4)) for _ in range(4))

@app.post("/api/generate", dependencies=[Depends(admin)])
def generate(b: Gen):
    now = int(time.time())
    keys = [f"DARK-{new_key()}" for _ in range(b.quantity)]
    with conn() as c:
        c.cursor().executemany(
            "INSERT INTO licenses(key,duration,active,created_at) VALUES(%s,%s,TRUE,%s)",
            [(k, b.duration, now) for k in keys],
        )
    return {"keys": keys}

@app.get("/api/keys", dependencies=[Depends(admin)])
def list_keys():
    now = int(time.time())
    with conn() as c:
        rows = c.execute("SELECT * FROM licenses ORDER BY created_at DESC, key").fetchall()
    return [
        {"key": r["key"], "status": status_of(r, now), "active": r["active"],
         "expires_at": r["expires_at"], "duration": r["duration"], "hwid": r["hwid"]}
        for r in rows
    ]

@app.post("/api/key/{key}/toggle", dependencies=[Depends(admin)])
def toggle(key: str):
    with conn() as c:
        cur = c.execute("UPDATE licenses SET active = NOT active WHERE key=%s", (key,))
        if not cur.rowcount: raise HTTPException(404, "الكود غير موجود")
    return {"ok": True}

@app.post("/api/key/{key}/extend", dependencies=[Depends(admin)])
def extend(key: str, b: Ext = Ext()):
    now = int(time.time())
    with conn() as c:
        r = c.execute("SELECT * FROM licenses WHERE key=%s", (key,)).fetchone()
        if not r: raise HTTPException(404, "الكود غير موجود")
        if r["expires_at"] is None:
            c.execute("UPDATE licenses SET duration = duration + %s WHERE key=%s", (b.seconds, key))
        else:
            c.execute("UPDATE licenses SET expires_at=%s WHERE key=%s", (max(r["expires_at"], now) + b.seconds, key))
    return {"ok": True}

@app.delete("/api/key/{key}", dependencies=[Depends(admin)])
def delete(key: str):
    with conn() as c:
        cur = c.execute("DELETE FROM licenses WHERE key=%s", (key,))
        if not cur.rowcount: raise HTTPException(404, "الكود غير موجود")
    return {"ok": True}

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE / "static" / "index.html")
