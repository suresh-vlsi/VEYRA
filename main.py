import hashlib
import hmac
import io
import os
import re
import secrets
import sqlite3
import string
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

import qrcode
import qrcode.image.svg
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl, Field
from starlette.middleware.sessions import SessionMiddleware

APP_NAME = "Linkly V3"
DB_PATH = os.environ.get("DB_PATH", "links.db")
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"
if not SESSION_SECRET:
    # Local-development fallback. Set a long random SESSION_SECRET before deployment.
    SESSION_SECRET = secrets.token_urlsafe(48)

os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
app = FastAPI(title=APP_NAME, version="3.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="linkly_session",
    same_site="lax",
    https_only=COOKIE_SECURE,
    max_age=60 * 60 * 24 * 7,
)
app.mount("/static", StaticFiles(directory="static"), name="static")

ALPHABET = string.ascii_letters + string.digits
RESERVED = {"docs", "redoc", "openapi", "api", "static", "health", "auth"}
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS links (
            code TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            clicks INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
        )""")
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(links)")}
        if "user_id" not in cols:
            conn.execute("ALTER TABLE links ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
        conn.execute("""CREATE TABLE IF NOT EXISTS click_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            ts TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            referrer TEXT NOT NULL DEFAULT 'Direct',
            device TEXT NOT NULL DEFAULT 'Other',
            browser TEXT NOT NULL DEFAULT 'Other',
            country TEXT NOT NULL DEFAULT 'Unknown'
        )""")
        event_cols = {r["name"] for r in conn.execute("PRAGMA table_info(click_events)")}
        if "country" not in event_cols:
            conn.execute("ALTER TABLE click_events ADD COLUMN country TEXT NOT NULL DEFAULT 'Unknown'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_code_ts ON click_events (code, ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_links_user ON links (user_id, created_at)")


init_db()


def base_url(request: Request) -> str:
    if BASE_URL:
        return BASE_URL.rstrip("/") + "/"

    scheme = request.headers.get(
        "x-forwarded-proto", request.url.scheme
    ).split(",")[0].strip()

    host = request.headers.get(
        "x-forwarded-host", request.headers.get("host", request.url.netloc)
    ).split(",")[0].strip()

    return f"{scheme}://{host}/"


def current_user(request: Request):
    uid = request.session.get("uid")
    if not uid:
        return None
    with db() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE id=?", (uid,)).fetchone()
    if not row:
        request.session.clear()
        return None
    return dict(row)


def require_user(request: Request):
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Please log in to continue")
    return user


def hash_password(password: str, salt_hex: str | None = None):
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return digest.hex(), salt.hex()


def verify_password(password: str, salt_hex: str, expected_hex: str) -> bool:
    actual, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(actual, expected_hex)


def parse_device(ua: str) -> str:
    u = ua.lower()
    if any(b in u for b in ("bot", "crawl", "spider", "preview", "curl", "python-requests")):
        return "Bot"
    if "ipad" in u or "tablet" in u:
        return "Tablet"
    if "mobi" in u or "android" in u or "iphone" in u:
        return "Mobile"
    return "Desktop"


def parse_browser(ua: str) -> str:
    u = ua.lower()
    if "edg/" in u or "edge/" in u: return "Edge"
    if "opr/" in u or "opera" in u: return "Opera"
    if "firefox" in u or "fxios" in u: return "Firefox"
    if "chrome" in u or "crios" in u: return "Chrome"
    if "safari" in u: return "Safari"
    return "Other"


def parse_referrer(ref: str) -> str:
    if not ref: return "Direct"
    return urlparse(ref).netloc or "Direct"


def country_from_headers(request: Request) -> str:
    # Cloudflare supplies CF-IPCountry when proxying through its network.
    country = request.headers.get("cf-ipcountry", "Unknown").upper()
    return country if re.fullmatch(r"[A-Z]{2}", country) else "Unknown"


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=10, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class LinkIn(BaseModel):
    url: HttpUrl
    custom_code: str | None = None


def new_code(conn, length=6):
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(length))
        if not conn.execute("SELECT 1 FROM links WHERE code=?", (code,)).fetchone():
            return code


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}


@app.get("/api/auth/me")
def auth_me(request: Request):
    return {"user": current_user(request)}


@app.post("/api/auth/register")
def register(payload: RegisterIn, request: Request):
    username = payload.username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(400, "Username must be 3–32 characters: letters, numbers, dot, underscore or hyphen")
    if len(payload.password) < 10:
        raise HTTPException(400, "Password must contain at least 10 characters")
    digest, salt = hash_password(payload.password)
    with db() as conn:
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            # Registration remains open; each account owns only its own links.
            pass
        try:
            cur = conn.execute("INSERT INTO users (username, password_hash, password_salt) VALUES (?, ?, ?)",
                               (username, digest, salt))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "That username is already registered")
        user_id = cur.lastrowid
        # Preserve the existing V2 data by assigning legacy unowned links to the first account only.
        if conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 1:
            conn.execute("UPDATE links SET user_id=? WHERE user_id IS NULL", (user_id,))
    request.session["uid"] = user_id
    return {"user": {"id": user_id, "username": username}}


@app.post("/api/auth/login")
def login(payload: LoginIn, request: Request):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (payload.username.strip(),)).fetchone()
    if not row or not verify_password(payload.password, row["password_salt"], row["password_hash"]):
        raise HTTPException(401, "Incorrect username or password")
    request.session.clear()
    request.session["uid"] = row["id"]
    return {"user": {"id": row["id"], "username": row["username"]}}


@app.post("/api/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"logged_out": True}


@app.post("/api/links")
def create_link(payload: LinkIn, request: Request):
    user = require_user(request)
    with db() as conn:
        code = payload.custom_code
        if code:
            if not code.isalnum() or len(code) > 32:
                raise HTTPException(400, "Custom code must be letters/numbers, max 32 chars")
            if code.lower() in RESERVED:
                raise HTTPException(400, "That code is reserved")
            if conn.execute("SELECT 1 FROM links WHERE code=?", (code,)).fetchone():
                raise HTTPException(409, "That code is already taken")
        else:
            code = new_code(conn)
        conn.execute("INSERT INTO links (code, url, user_id) VALUES (?, ?, ?)",
                     (code, str(payload.url), user["id"]))
    return {"code": code, "short_url": f"{base_url(request)}{code}", "url": str(payload.url)}


@app.get("/api/links")
def list_links(request: Request):
    user = require_user(request)
    with db() as conn:
        rows = conn.execute(
            "SELECT code, url, clicks, created_at FROM links WHERE user_id=? ORDER BY created_at DESC, rowid DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
    root = base_url(request)
    return [{**dict(r), "short_url": f"{root}{r['code']}"} for r in rows]


@app.delete("/api/links/{code}")
def delete_link(code: str, request: Request):
    user = require_user(request)
    with db() as conn:
        cur = conn.execute("DELETE FROM links WHERE code=? AND user_id=?", (code, user["id"]))
        if cur.rowcount == 0:
            raise HTTPException(404, "Link not found")
        conn.execute("DELETE FROM click_events WHERE code=?", (code,))
    return {"deleted": code}


@app.get("/api/links/{code}/qr")
def qr_code(code: str, request: Request):
    user = require_user(request)
    with db() as conn:
        if not conn.execute("SELECT 1 FROM links WHERE code=? AND user_id=?", (code, user["id"])).fetchone():
            raise HTTPException(404, "Link not found")
    img = qrcode.make(f"{base_url(request)}{code}", image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO(); img.save(buf)
    return Response(
       content=buf.getvalue(),
       media_type="image/svg+xml",
       headers={
        "Content-Disposition": f'attachment; filename="{code}-qr.svg"'
       }
    )


@app.get("/api/links/{code}/stats")
def link_stats(code: str, request: Request):
    user = require_user(request)
    days = 30
    with db() as conn:
        link = conn.execute("SELECT clicks FROM links WHERE code=? AND user_id=?", (code, user["id"])).fetchone()
        if not link: raise HTTPException(404, "Link not found")
        start = (date.today() - timedelta(days=days - 1)).isoformat()
        rows = conn.execute("SELECT date(ts) AS d, COUNT(*) AS n FROM click_events WHERE code=? AND date(ts)>=? GROUP BY d", (code, start)).fetchall()
        counts = {r["d"]: r["n"] for r in rows}
        def breakdown(column, limit=8):
            allowed = {"referrer", "device", "browser", "country"}
            if column not in allowed: return []
            data = conn.execute(f"SELECT {column} AS name, COUNT(*) AS n FROM click_events WHERE code=? GROUP BY name ORDER BY n DESC LIMIT ?", (code, limit)).fetchall()
            return [{"name": r["name"], "count": r["n"]} for r in data]
        daily = [{"date": (date.today()-timedelta(days=days-1-i)).isoformat(),
                  "count": counts.get((date.today()-timedelta(days=days-1-i)).isoformat(), 0)} for i in range(days)]
        result = {"total": link["clicks"], "period_days": days, "per_day": daily,
                  "referrers": breakdown("referrer"), "devices": breakdown("device"),
                  "browsers": breakdown("browser"), "countries": breakdown("country")}
    return result


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.get("/{code}")
def follow(code: str, request: Request):
    ua = request.headers.get("user-agent", "")
    with db() as conn:
        row = conn.execute("SELECT url FROM links WHERE code=?", (code,)).fetchone()
        if not row: raise HTTPException(404, "Link not found")
        conn.execute("UPDATE links SET clicks=clicks+1 WHERE code=?", (code,))
        conn.execute("INSERT INTO click_events (code, referrer, device, browser, country) VALUES (?, ?, ?, ?, ?)",
                     (code, parse_referrer(request.headers.get("referer", "")), parse_device(ua), parse_browser(ua), country_from_headers(request)))
    return RedirectResponse(row["url"], status_code=307)
