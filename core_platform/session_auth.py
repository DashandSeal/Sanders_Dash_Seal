"""Session authentication for the Sanders Dash & Seal customer app.

Minimal username/password session auth backed by SQLite, using only the
standard library (``hashlib.scrypt`` for password hashes, ``secrets`` for
session tokens). No new external dependencies, no seeded accounts, no
invented credentials.

Roles: CUSTOMER (registers through ``/auth/register``) and OPERATOR (created
once, through ``/auth/setup`` with the owner-held setup token
``SDS_OWNER_SETUP_TOKEN``). The setup route works only while no OPERATOR
account exists and only while the token is set; with the token unset, or
once an operator exists, setup is unavailable (fail closed). The operator
is the human who approves quotes; the customer app asks this module
``operator_verifier(identity)`` for that decision.

``authenticate(env)`` is the independent session verifier the customer app
calls: it reads the ``session`` cookie and returns the username, or None.
Issuing a session rotates it: every prior session for the account is
invalidated at login/register/setup (Phase A remediation, 2026-11-24),
and the setup token is compared in constant time.
``auth_app`` is the WSGI app behind ``/auth/login`` / ``/auth/register`` /
``/auth/setup`` / ``/auth/logout`` (POST only, JSON in and out, same
``{ok, role}`` / ``{error}`` shape ``web/auth.js`` already expects,
including the ``try_again_later`` lockout error after repeated failures).
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from urllib.parse import urlparse

IDENT = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

SESSION_TTL_SECONDS = 7 * 86400
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 900
MIN_PASSWORD_LENGTH = 8


class SessionAuthError(ValueError):
    """Raised when an auth operation is denied; message is safe to return."""


def _hash_password(password, salt):
    return hashlib.scrypt(
        password.encode('utf-8'), salt=salt,
        n=2 ** 14, r=8, p=1, dklen=64).hex()


class SessionAuth:
    """SQLite-backed accounts + sessions for the customer app."""

    def __init__(self, db_path, site_origin, *, setup_token=None,
                 allowed_origins=None, clock=time.time):
        origin = urlparse(site_origin)
        if (origin.scheme != 'https' or not origin.netloc or origin.path
                or origin.query or origin.fragment or origin.username):
            raise SessionAuthError('Trusted origin required')
        self.db_path = str(db_path)
        self.site_origin = site_origin
        self.setup_token = setup_token
        self.allowed_origins = (
            frozenset(allowed_origins) if allowed_origins is not None
            else frozenset((site_origin,)))
        self.clock = clock
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS sds_accounts (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('CUSTOMER', 'OPERATOR')),
                created_at INTEGER NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                locked_until INTEGER NOT NULL DEFAULT 0)''')
            db.execute('''CREATE TABLE IF NOT EXISTS sds_sessions (
                token TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL)''')

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    # -- identity ---------------------------------------------------------

    def authenticate(self, env):
        """Return the session username, or None when there is no live session."""
        try:
            cookie = env.get('HTTP_COOKIE', '')
            if not isinstance(cookie, str):
                return None
            token = None
            for part in cookie.split(';'):
                part = part.strip()
                if part.startswith('session='):
                    token = part[len('session='):]
                    break
            if not token:
                return None
            with self._connect() as db:
                row = db.execute(
                    'SELECT username, expires_at FROM sds_sessions WHERE token = ?;',
                    (token,)).fetchone()
                if row is None:
                    return None
                if row['expires_at'] <= self.clock():
                    db.execute('DELETE FROM sds_sessions WHERE token = ?;', (token,))
                    db.commit()
                    return None
                return row['username']
        except Exception:
            return None

    def operator_verifier(self, identity):
        """True only when the identity holds an OPERATOR account."""
        try:
            if not isinstance(identity, str) or not IDENT.fullmatch(identity):
                return False
            with self._connect() as db:
                row = db.execute(
                    'SELECT role FROM sds_accounts WHERE username = ?;',
                    (identity,)).fetchone()
                return row is not None and row['role'] == 'OPERATOR'
        except Exception:
            return False

    # -- accounts ---------------------------------------------------------

    def _create_account(self, db, username, password, role):
        if not isinstance(username, str) or not IDENT.fullmatch(username):
            raise SessionAuthError('invalid_username')
        if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
            raise SessionAuthError('invalid_password')
        salt = secrets.token_bytes(16)
        try:
            db.execute(
                'INSERT INTO sds_accounts '
                '(username, password_hash, salt, role, created_at) '
                'VALUES (?, ?, ?, ?, ?);',
                (username, _hash_password(password, salt), salt.hex(),
                 role, int(self.clock())))
        except sqlite3.IntegrityError as exc:
            raise SessionAuthError('username_taken') from exc

    def _open_session(self, db, username):
        # Session rotation (Phase A remediation, 2026-11-24 — inventory
        # finding F-6): issuing a session invalidates every prior
        # session for the account, so a stolen token's life ends at the
        # account's next sign-in instead of running to its own expiry,
        # and a fresh login is proof the old credentials are dead.
        db.execute('DELETE FROM sds_sessions WHERE username = ?;', (username,))
        token = secrets.token_urlsafe(32)
        now = int(self.clock())
        db.execute(
            'INSERT INTO sds_sessions (token, username, expires_at, created_at) '
            'VALUES (?, ?, ?, ?);',
            (token, username, now + SESSION_TTL_SECONDS, now))
        return token

    def _check_password(self, db, username, password):
        """Verify a password; enforce the failed-attempt lockout.

        Returns the account role on success. Raises SessionAuthError
        ('sign_in_failed' or 'try_again_later') on failure.
        """
        row = db.execute(
            'SELECT password_hash, salt, role, failed_attempts, locked_until '
            'FROM sds_accounts WHERE username = ?;', (username,)).fetchone()
        if row is None:
            raise SessionAuthError('sign_in_failed')
        now = int(self.clock())
        if row['locked_until'] > now:
            raise SessionAuthError('try_again_later')
        expected = _hash_password(password, bytes.fromhex(row['salt']))
        if not hmac.compare_digest(expected, row['password_hash']):
            failed = row['failed_attempts'] + 1
            locked_until = (now + LOCKOUT_SECONDS
                            if failed >= MAX_FAILED_ATTEMPTS else 0)
            db.execute(
                'UPDATE sds_accounts SET failed_attempts = ?, locked_until = ? '
                'WHERE username = ?;', (failed, locked_until, username))
            db.commit()
            raise SessionAuthError(
                'try_again_later' if locked_until else 'sign_in_failed')
        db.execute(
            'UPDATE sds_accounts SET failed_attempts = 0, locked_until = 0 '
            'WHERE username = ?;', (username,))
        db.commit()
        return row['role']

    # -- WSGI auth app ----------------------------------------------------

    def auth_app(self, env, start):
        """POST /auth/login | /auth/register | /auth/setup | /auth/logout."""
        path = env.get('PATH_INFO', '')
        method = env.get('REQUEST_METHOD', '')
        try:
            if method != 'POST':
                return self._respond(start, '405 Method Not Allowed',
                                     {'error': 'method_not_allowed'},
                                     [('Allow', 'POST')])
            if env.get('HTTP_ORIGIN') not in self.allowed_origins:
                return self._respond(start, '403 Forbidden',
                                     {'error': 'origin_denied'})
            if env.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
                return self._respond(start, '415 Unsupported Media Type',
                                     {'error': 'json_required'})
            try:
                length = env.get('CONTENT_LENGTH', '')
                if not isinstance(length, str) or not length.isdigit() or not 0 < int(length) <= 4096:
                    raise ValueError('length')
                raw = env['wsgi.input'].read(int(length))
                if len(raw) != int(length):
                    raise ValueError('short body')
                data = json.loads(raw)
                if not isinstance(data, dict):
                    raise ValueError('object required')
            except (ValueError, UnicodeError, KeyError, TypeError, json.JSONDecodeError):
                return self._respond(start, '400 Bad Request',
                                     {'error': 'invalid_request'})

            if path == '/auth/login':
                return self._login(start, data)
            if path == '/auth/register':
                return self._register(start, data)
            if path == '/auth/setup':
                return self._setup(start, data)
            if path == '/auth/logout':
                return self._logout(env, start)
            return self._respond(start, '404 Not Found', {'error': 'not_found'})
        except SessionAuthError as exc:
            status = ('429 Too Many Requests' if str(exc) == 'try_again_later'
                      else '400 Bad Request')
            return self._respond(start, status, {'error': str(exc)})
        except Exception:
            return self._respond(start, '503 Service Unavailable',
                                 {'error': 'temporarily_unavailable'})

    def _login(self, start, data):
        if set(data) != {'username', 'password'}:
            raise SessionAuthError('invalid_request')
        with self._connect() as db:
            role = self._check_password(db, data['username'], data['password'])
            token = self._open_session(db, data['username'])
            db.commit()
        return self._respond(start, '200 OK', {'ok': True, 'role': role},
                             self._cookie_headers(token))

    def _register(self, start, data):
        if set(data) != {'username', 'password'}:
            raise SessionAuthError('invalid_request')
        with self._connect() as db:
            self._create_account(db, data['username'], data['password'], 'CUSTOMER')
            token = self._open_session(db, data['username'])
            db.commit()
        return self._respond(start, '200 OK', {'ok': True, 'role': 'CUSTOMER'},
                             self._cookie_headers(token))

    def _setup(self, start, data):
        if set(data) != {'username', 'password', 'setup_token'}:
            raise SessionAuthError('invalid_request')
        # Constant-time comparison (Phase A remediation, 2026-11-24 —
        # finding F-6): the owner-held setup token is compared with
        # hmac.compare_digest, never !=, so its value cannot be probed
        # through response timing.
        provided = data['setup_token']
        if (not self.setup_token or not isinstance(provided, str)
                or not hmac.compare_digest(provided, self.setup_token)):
            return self._respond(start, '503 Service Unavailable',
                                 {'error': 'setup_unavailable'})
        with self._connect() as db:
            existing = db.execute(
                "SELECT 1 FROM sds_accounts WHERE role = 'OPERATOR' LIMIT 1;"
            ).fetchone()
            if existing is not None:
                return self._respond(start, '403 Forbidden',
                                     {'error': 'setup_unavailable'})
            self._create_account(db, data['username'], data['password'], 'OPERATOR')
            token = self._open_session(db, data['username'])
            db.commit()
        return self._respond(start, '200 OK', {'ok': True, 'role': 'OPERATOR'},
                             self._cookie_headers(token))

    def _logout(self, env, start):
        try:
            cookie = env.get('HTTP_COOKIE', '')
            token = None
            for part in cookie.split(';'):
                part = part.strip()
                if part.startswith('session='):
                    token = part[len('session='):]
                    break
            if token:
                with self._connect() as db:
                    db.execute('DELETE FROM sds_sessions WHERE token = ?;', (token,))
                    db.commit()
        except Exception:
            pass
        return self._respond(start, '200 OK', {'ok': True},
                             [('Set-Cookie', 'session=; Path=/; Max-Age=0; '
                                            'HttpOnly; SameSite=Lax; Secure')])

    def _cookie_headers(self, token):
        return [('Set-Cookie',
                 f'session={token}; Path=/; Max-Age={SESSION_TTL_SECONDS}; '
                 'HttpOnly; SameSite=Lax; Secure')]

    @staticmethod
    def _respond(start, status, data, extra=()):
        body = json.dumps(data, separators=(',', ':')).encode()
        start(status, [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(body))),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Referrer-Policy', 'no-referrer'),
            *extra,
        ])
        return [body]


def create_session_auth(db_path, site_origin, *, setup_token=None,
                        allowed_origins=None):
    """Build the session auth for a deployment boundary.

    ``setup_token`` comes from the environment (``SDS_OWNER_SETUP_TOKEN``);
    pass None and the setup route stays unavailable.
    """
    return SessionAuth(db_path, site_origin, setup_token=setup_token,
                       allowed_origins=allowed_origins)
