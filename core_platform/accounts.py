"""
Module: core_platform.accounts
Architectural Layer: Persistent Account Authentication & Rate-Limiting Core
Description: Handles cryptographic password hashing, secure token generation,
             session authorization matrices, and rate-limiting throttles.
"""

from http.cookies import SimpleCookie, CookieError
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid

COOKIE = '__Host-sds_session'
USER_RE = re.compile(r'^[a-z0-9]([a-z0-9_-]|\.){2,63}$', re.ASCII)
TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{43}$', re.ASCII)

class AccountDenied(ValueError): pass
class RateLimited(AccountDenied): pass

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password_hash(password, salt):
    if not isinstance(password, str) or not 15 <= len(password) <= 128:
        raise AccountDenied('Use a passphrase of 15 to 128 characters')
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1, maxmem=32*1024*1024, dklen=32).hex()

class AccountStore:
    def __init__(self, self_path, setup_digest=None, setup_expires=0, clock=time.time):
        self.path = self_path
        self.clock = clock
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS customer_accounts (
                actor TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, salt TEXT NOT NULL,
                password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('CUSTOMER', 'OPERATOR')));""")
            db.execute("""CREATE TABLE IF NOT EXISTS customer_sessions (
                digest TEXT PRIMARY KEY, actor TEXT NOT NULL REFERENCES customer_accounts(actor),
                issued REAL NOT NULL, seen REAL NOT NULL, expires REAL NOT NULL, kind TEXT NOT NULL,
                parent TEXT);""")
            db.execute("""CREATE TABLE IF NOT EXISTS account_throttles (
                bucket TEXT NOT NULL, window INTEGER NOT NULL, attempts INTEGER NOT NULL,
                PRIMARY KEY(bucket, window));""")
            db.execute("""CREATE TABLE IF NOT EXISTS owner_setup (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), digest TEXT NOT NULL,
                expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);""")
            if setup_digest is not None:
                if not re.fullmatch(r'[0-9a-f]{64}', setup_digest) or type(setup_expires) not in (int, float):
                    raise AccountDenied('Invalid owner setup configuration')
                db.execute('INSERT OR IGNORE INTO owner_setup(singleton, digest, expires) VALUES (1, ?, ?);', (setup_digest, setup_expires))

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute('PRAGMA foreign_keys=ON;')
        db.row_factory = sqlite3.Row
        return db

    def throttle(self, username, limit=10):
        window = int(self.clock()) // 60
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM account_throttles WHERE window < ?;', (window - 2,))
            for bucket in (f'global_100', digest(username)):
                db.execute("""INSERT INTO account_throttles VALUES (?, ?, 1)
                              ON CONFLICT(bucket, window) DO UPDATE SET attempts=attempts+1;""", (bucket, window))
                
                # FIX: Explicitly extract the row value integer using fetchone() to prevent type comparison errors
                row = db.execute('SELECT attempts FROM account_throttles WHERE bucket=? AND window=?;', (bucket, window)).fetchone()
                attempts = row[0] if row else 0
                
                if attempts > limit:
                    db.commit()
                    raise RateLimited('Try again shortly')
            db.commit()

    def register(self, username, password, setup_token=None):
        if not isinstance(username, str) or not USER_RE.fullmatch(username):
            raise AccountDenied('Invalid account name')
        salt = secrets.token_hex(16)
        hashed = password_hash(password, salt)
        actor = 'account-' + str(uuid.uuid4())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            role = 'CUSTOMER'
            if setup_token is not None:
                row = db.execute('SELECT * FROM owner_setup WHERE singleton=1;').fetchone()
                if not row or row['used'] or self.clock() >= row['expires'] or not hmac.compare_digest(digest(setup_token), row['digest']):
                    raise AccountDenied('Owner setup unavailable')
                if db.execute('SELECT 1 FROM customer_accounts WHERE role="OPERATOR";').fetchone():
                    raise AccountDenied('Owner already configured')
                role = 'OPERATOR'
            try:
                db.execute('INSERT INTO customer_accounts VALUES (?, ?, ?, ?, ?);', (actor, username, salt, hashed, role))
            except sqlite3.IntegrityError:
                raise AccountDenied('Account unavailable')
            if role == 'OPERATOR':
                db.execute('UPDATE owner_setup SET used=1 WHERE singleton=1;')
        return actor

    def login(self, username, password):
        if not isinstance(username, str) or not USER_RE.fullmatch(username):
            raise AccountDenied('Sign-in failed')
        with self.connect() as db:
            row = db.execute('SELECT * FROM customer_accounts WHERE username=?;', (username,)).fetchone()
        salt = row['salt'] if row else '0' * 32
        hashed = password_hash(password, salt)
        if not row or not hmac.compare_digest(row['password_hash'], hashed):
            raise AccountDenied('Sign-in failed')
        return row['actor']

    def issue(self, actor, kind='BROWSER', parent=None):
        token = secrets.token_urlsafe(32)
        now = self.clock()
        with self.connect() as db:
            db.execute('DELETE FROM customer_sessions WHERE expires <= ? OR seen < ?;', (now, now - 1800))
            db.execute('INSERT INTO customer_sessions VALUES (?, ?, ?, ?, ?, ?, ?);',
                       (digest(token), actor, now, now, now + (600 if kind == 'API' else 28800), kind, parent))
        return token

    def credential(self, env):
        authorization = env.get('HTTP_AUTHORIZATION')
        if authorization is not None:
            if not isinstance(authorization, str) or not authorization.startswith('Bearer '):
                return None
            return authorization[7:]
        cookie = env.get('HTTP_COOKIE', '')
        if not isinstance(cookie, str) or len(cookie) > 4096:
            return None
        try:
            parsed = SimpleCookie()
            parsed.load(cookie)
            token = parsed[COOKIE].value if COOKIE in parsed else None
        except CookieError:
            return None
        return token if isinstance(token, str) and TOKEN_RE.fullmatch(token) else None

    def authenticate(self, env):
        token = self.credential(env)
        if token is None:
            return None
        now = self.clock()
        with self.connect() as db:
            row = db.execute('SELECT * FROM customer_sessions WHERE digest=?;', (digest(token),)).fetchone()
            if not row or now >= row['expires'] or now - row['seen'] >= 1800:
                return None
            if row['parent']:
                parent_row = db.execute('SELECT * FROM customer_sessions WHERE digest=?;', (row['parent'],)).fetchone()
                if not parent_row or now >= parent_row['expires'] or now - parent_row['seen'] >= 1800:
                    return None
            db.execute('UPDATE customer_sessions SET seen=? WHERE digest=?;', (now, digest(token)))
        return row['actor']

    def operator(self, actor):
        with self.connect() as db:
            row = db.execute('SELECT role FROM customer_accounts WHERE actor=?;', (actor,)).fetchone()
        return bool(row and row['role'] == 'OPERATOR')

    def logout(self, env):
        token = self.credential(env)
        if token:
            with self.connect() as db:
                db.execute('DELETE FROM customer_sessions WHERE digest=? OR parent=?;', (digest(token), digest(token)))

    def api_token(self, env):
        actor = self.authenticate(env)
        if actor is None:
            raise AccountDenied('Sign in first')
        with self.connect() as db:
            row = db.execute('SELECT kind FROM customer_sessions WHERE digest=?;', (digest(self.credential(env)),)).fetchone()
        if not row or row['kind'] != 'BROWSER':
            raise AccountDenied('Browser session required')
        self.throttle(actor)
        return self.issue(actor, kind='API', parent=digest(self.credential(env)))

def auth_app(accounts, origin):
    def application(env, start):
        def response(status, value, headers=None):
            body = json.dumps(value, separators=(',', ':')).encode()
            start(status, [('Content-Type', 'application/json'), ('Content-Length', str(len(body))),
                           ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')] + (headers or []))
            return [body]
            
        path = env.get('PATH_INFO', '')
        if path not in ('/auth/login', '/auth/register', '/auth/logout', '/auth/setup', '/auth/token'):
            return response('404 Not Found', {'error': 'not_found'})
        if env.get('REQUEST_METHOD') != 'POST':
            return response('405 Method Not Allowed', {'error': 'post_required'})
        if env.get('HTTP_ORIGIN') != origin:
            return response('403 Forbidden', {'error': 'origin_denied'})
        if env.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
            return response('415 Unsupported Media Type', {'error': 'json_required'})
            
        try:
            content_length = int(env.get('CONTENT_LENGTH', '0'))
            if not 0 < content_length <= 2048:
                raise ValueError()
                
