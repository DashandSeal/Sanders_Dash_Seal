"""
Module: core_platform.accounts
Architectural Layer: Persistent Account Authentication & Rate Limiting Core
Description: Handles cryptographic password hashing, secure token generation,
session authorization matrices, and rate-limiting throttles.
"""

from http.cookies import SimpleCookie, CookieError
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
import uuid

COOKIE = "__Host-ads_session"
USER_RE = re.compile(r'^[a-z0-9_.-]{1,64}$', re.ASCII)
TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{43}$', re.ASCII)

class AccountDenied(ValueError):
    """Custom exception raised when account authentication or authorization fails."""
    pass

class RateLimited(AccountDenied):
    """Custom exception raised when rate limit thresholds are exceeded."""
    pass

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def password_hash(password, salt=None):
    if not isinstance(password, str) or not 15 <= len(password) <= 128:
        raise AccountDenied('Use a passphrase of 15 to 128 characters')
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16328, r=8, p=1).hex()
    return f"{salt}${hashed}"

class AccountStore:
    """Manages secure customer accounts, sessions, throttling, and initialization."""
    
    def __init__(self, db_path, setup_digest=None, setup_expires=0, clock=time.time):
        self.path = db_path
        self.clock = clock
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS customer_accounts (
                actor TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('OPERATOR', 'CUSTOMER'))
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS customer_sessions (
                digest TEXT PRIMARY KEY, actor TEXT NOT NULL REFERENCES customer_accounts(actor),
                issued REAL NOT NULL, seen REAL NOT NULL, expires REAL NOT NULL, parent TEXT
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS account_throttles (
                bucket TEXT NOT NULL, window INTEGER NOT NULL, attempts INTEGER NOT NULL,
                PRIMARY KEY(bucket, window)
            );""")
            db.execute("""CREATE TABLE IF NOT EXISTS owner_setup (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), digest TEXT NOT NULL,
                expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0
            );""")
            if setup_digest is not None:
                if not re.fullmatch(r'[0-9a-f]{64}', setup_digest):
                    raise AccountDenied('Invalid owner setup configuration')
                db.execute("INSERT OR IGNORE INTO owner_setup(singleton, digest, expires) VALUES (1, ?, ?);", 
                           (setup_digest, setup_expires))

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON;")
        db.row_factory = sqlite3.Row
        return db

    def throttle(self, bucket, username, limit=10):
        window = int(self.clock()) // 60
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            db.execute("DELETE FROM account_throttles WHERE window < ?;", (window - 5,))
            db.execute("""
                INSERT INTO account_throttles (bucket, window, attempts) VALUES (?, ?, 1)
                ON CONFLICT(bucket, window) DO UPDATE SET attempts = attempts + 1;
            """, (f"{bucket}_{username}", window))
            
            row = db.execute("SELECT attempts FROM account_throttles WHERE bucket = ? AND window = ?;", 
                             (f"{bucket}_{username}", window)).fetchone()
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
        actor = f"account-{str(uuid.uuid4())}"
        
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE;")
            role = 'CUSTOMER'
            if setup_token is not None:
                row = db.execute("SELECT * FROM owner_setup WHERE singleton = 1").fetchone()
                if not row or row['used'] or row['expires'] < self.clock():
                    raise AccountDenied('Owner setup unavailable')
                if not hmac.compare_digest(digest(setup_token), row['digest']):
                    raise AccountDenied('Invalid setup token')
                role = 'OPERATOR'
            
            try:
                db.execute("INSERT INTO customer_accounts VALUES (?, ?, ?, ?);", 
                           (actor, username, hashed, role))
            except sqlite3.IntegrityError as exc:
                raise AccountDenied('Account unavailable') from exc
            
            if role == 'OPERATOR':
                db.execute("UPDATE owner_setup SET used = 1 WHERE singleton = 1;")
            db.commit()
        return actor

    def login(self, username, password):
        if not isinstance(username, str) or not USER_RE.fullmatch(username):
            raise AccountDenied('Sign-in failed')
        
        with self._connect() as db:
            row = db.execute("SELECT * FROM customer_accounts WHERE username = ?;", (username,)).fetchone()
            if not row:
                raise AccountDenied('Sign-in failed')
            
            parts = row['password_hash'].split('$')
            if len(parts) != 2:
                raise AccountDenied('Sign-in failed')
            
            salt, stored_hash = parts
            computed = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16328, r=8, p=1).hex()
            
            if not hmac.compare_digest(stored_hash, computed):
                raise AccountDenied('Sign-in failed')
            return row['actor']

    def issue(self, actor, kind='BROWSER', parent=None):
        token = secrets.token_urlsafe(32)
        token_digest = digest(token)
        now = self.clock()
        
        with self._connect() as db:
            db.execute("DELETE FROM customer_sessions WHERE expires <= ?;", (now,))
            db.execute("INSERT INTO customer_sessions VALUES (?, ?, ?, ?, ?, ?);", 
                       (token_digest, actor, now, now, now + 86400, parent))
            db.commit()
        return token

    def credential(self, env):
        authorization = env.get('HTTP_AUTHORIZATION')
        if authorization:
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
        if not token:
            return None
        
        token_digest = digest(token)
        now = self.clock()
        
        with self._connect() as db:
            row = db.execute("SELECT * FROM customer_sessions WHERE digest = ?;", (token_digest,)).fetchone()
            if not row or row['expires'] < now or row['seen'] < now - 86400:
                return None
            
            if row['parent']:
                parent_row = db.execute("SELECT * FROM customer_sessions WHERE digest = ?;", (row['parent'],)).fetchone()
                if not parent_row or parent_row['expires'] < now:
                    return None
            
            db.execute("UPDATE customer_sessions SET seen = ? WHERE digest = ?;", (now, token_digest))
            db.commit()
            return row['actor']

    def operator(self, actor):
        with self._connect() as db:
            row = db.execute("SELECT role FROM customer_accounts WHERE actor = ?;", (actor,)).fetchone()
            return bool(row and row['role'] == 'OPERATOR')

    def logout(self, env):
        token = self.credential(env)
        if token:
            with self._connect() as db:
                db.execute("DELETE FROM customer_sessions WHERE digest = ?;", (digest(token),))
                db.commit()

    def api_token(self, env):
        actor = self.authenticate(env)
        if not actor:
            raise AccountDenied('Sign in first')
        with self._connect() as db:
            row = db.execute("SELECT kind FROM customer_sessions WHERE actor = ?;", (actor,)).fetchone()
            if not row or row['kind'] != 'BROWSER':
                raise AccountDenied('Browser session required')
        self.throttle('api', actor)
        return self.issue(actor, kind='API', parent=digest(self.credential(env)))
