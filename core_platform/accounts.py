"""Persistent account authentication; accounts do not establish notarial identity."""
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
import json
import re
import secrets
import sqlite3
import time
import uuid

COOKIE='__Host-sds_session'
USER=re.compile(r'[a-z0-9][a-z0-9_.-]{2,63}',re.ASCII)
TOKEN=re.compile(r'[A-Za-z0-9_-]{43}',re.ASCII)


class AccountDenied(ValueError): pass
class RateLimited(AccountDenied): pass


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password,salt):
    if not isinstance(password,str) or not 15<=len(password)<=128:
        raise AccountDenied('Use a passphrase of 15 to 128 characters')
    return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=2**14,r=8,p=5,
                          maxmem=32*1024*1024,dklen=32).hex()


class AccountStore:
    def __init__(self,path,*,setup_digest=None,setup_expires=0,clock=time.time):
        self.path,self.clock=str(path),clock
        with self.connect() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS customer_accounts (
                actor TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, salt TEXT NOT NULL,
                password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('CUSTOMER','OPERATOR')));
                CREATE TABLE IF NOT EXISTS customer_sessions (
                digest TEXT PRIMARY KEY, actor TEXT NOT NULL REFERENCES customer_accounts(actor),
                issued REAL NOT NULL, seen REAL NOT NULL, expires REAL NOT NULL, kind TEXT NOT NULL,
                parent TEXT);
                CREATE TABLE IF NOT EXISTS account_throttles (bucket TEXT NOT NULL, window INTEGER NOT NULL,
                attempts INTEGER NOT NULL, PRIMARY KEY(bucket,window));
                CREATE TABLE IF NOT EXISTS owner_setup (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), digest TEXT NOT NULL,
                expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);''')
            if setup_digest is not None:
                if not re.fullmatch('[0-9a-f]{64}',setup_digest) or type(setup_expires) not in (int,float):
                    raise AccountDenied('Invalid owner setup configuration')
                db.execute('INSERT OR IGNORE INTO owner_setup(singleton,digest,expires) VALUES (1,?,?)',
                           (setup_digest,setup_expires))

    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.execute('PRAGMA foreign_keys=ON');db.row_factory=sqlite3.Row
        return db

    def throttle(self,username):
        window=int(self.clock()//60)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM account_throttles WHERE window < ?', (window-2,))
            for bucket,limit in [('global',100),(digest(username),10)]:
                db.execute('INSERT INTO account_throttles VALUES (?,?,1) ON CONFLICT(bucket,window) '
                           'DO UPDATE SET attempts=attempts+1',(bucket,window))
                n=db.execute('SELECT attempts FROM account_throttles WHERE bucket=? AND window=?',
                             (bucket,window)).fetchone()[0]
                # Commit failed attempts too; an exception inside the transaction would roll them back.
                if n>limit:
                    db.commit();raise RateLimited('Try again shortly')

    def register(self,username,password,*,setup_token=None):
        if not isinstance(username,str) or not USER.fullmatch(username):raise AccountDenied('Invalid account name')
        salt=secrets.token_hex(16);hashed=password_hash(password,salt)
        actor='account-'+uuid.uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');role='CUSTOMER'
            if setup_token is not None:
                row=db.execute('SELECT * FROM owner_setup WHERE singleton=1').fetchone()
                if (not isinstance(setup_token,str) or not TOKEN.fullmatch(setup_token) or not row
                    or row['used'] or self.clock()>=row['expires']
                    or not hmac.compare_digest(row['digest'],digest(setup_token))):
                    raise AccountDenied('Owner setup unavailable')
                if db.execute("SELECT 1 FROM customer_accounts WHERE role='OPERATOR'").fetchone():
                    raise AccountDenied('Owner already configured')
                role='OPERATOR'
            try:db.execute('INSERT INTO customer_accounts VALUES (?,?,?,?,?)',(actor,username,salt,hashed,role))
            except sqlite3.IntegrityError:raise AccountDenied('Account unavailable') from None
            if role=='OPERATOR':db.execute('UPDATE owner_setup SET used=1 WHERE singleton=1')
        return actor

    def login(self,username,password):
        if not isinstance(username,str) or not USER.fullmatch(username):raise AccountDenied('Sign-in failed')
        with self.connect() as db:row=db.execute('SELECT * FROM customer_accounts WHERE username=?',(username,)).fetchone()
        salt=row['salt'] if row else '0'*32
        hashed=password_hash(password,salt)
        if not row or not hmac.compare_digest(row['password_hash'],hashed):raise AccountDenied('Sign-in failed')
        return self.issue(row['actor'])

    def issue(self,actor,*,kind='BROWSER',parent=None):
        token=secrets.token_urlsafe(32);now=self.clock()
        with self.connect() as db:
            db.execute('DELETE FROM customer_sessions WHERE expires <= ? OR seen <= ?', (now,now-1800))
            db.execute('INSERT INTO customer_sessions VALUES (?,?,?,?,?,?,?)',
                       (digest(token),actor,now,now,now+(600 if kind=='API' else 28800),kind,parent))
        return token

    @staticmethod
    def credential(env):
        authorization=env.get('HTTP_AUTHORIZATION')
        if authorization is not None:
            if not isinstance(authorization,str) or not authorization.startswith('Bearer '):return None
            token=authorization[7:]
        else:
            cookie=env.get('HTTP_COOKIE','')
            if not isinstance(cookie,str) or len(cookie)>4096:return None
            try:
                parsed=SimpleCookie();parsed.load(cookie)
                token=parsed[COOKIE].value if COOKIE in parsed else None
            except CookieError:return None
        return token if isinstance(token,str) and TOKEN.fullmatch(token) else None

    def authenticate(self,env):
        token=self.credential(env)
        if token is None:return None
        now=self.clock()
        with self.connect() as db:
            row=db.execute('SELECT * FROM customer_sessions WHERE digest=?',(digest(token),)).fetchone()
            if not row or now>=row['expires'] or now-row['seen']>=1800:return None
            if row['parent']:
                parent=db.execute('SELECT * FROM customer_sessions WHERE digest=?',(row['parent'],)).fetchone()
                if not parent or now>=parent['expires'] or now-parent['seen']>=1800:return None
            db.execute('UPDATE customer_sessions SET seen=? WHERE digest=?',(now,digest(token)))
        return row['actor']

    def operator(self,actor):
        with self.connect() as db:row=db.execute('SELECT role FROM customer_accounts WHERE actor=?',(actor,)).fetchone()
        return bool(row and row['role']=='OPERATOR')

    def logout(self,env):
        token=self.credential(env)
        if token:
            with self.connect() as db:
                db.execute('DELETE FROM customer_sessions WHERE digest=? OR parent=?',(digest(token),digest(token)))

    def api_token(self,env):
        actor=self.authenticate(env);token=self.credential(env)
        if actor is None:raise AccountDenied('Sign in first')
        with self.connect() as db:row=db.execute('SELECT kind FROM customer_sessions WHERE digest=?',(digest(token),)).fetchone()
        if not row or row['kind']!='BROWSER':raise AccountDenied('Browser session required')
        self.throttle('api-token:'+actor)
        return self.issue(actor,kind='API',parent=digest(token))


def auth_app(accounts,origin):
    def application(env,start):
        def respond(status,value,headers=()):
            body=json.dumps(value,separators=(',',':')).encode()
            start(status,[('Content-Type','application/json'),('Content-Length',str(len(body))),
                ('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),*headers]);return [body]
        path=env.get('PATH_INFO','')
        if path not in ('/auth/login','/auth/register','/auth/logout','/auth/setup','/auth/token'):
            return respond('404 Not Found',{'error':'not_found'})
        if env.get('REQUEST_METHOD')!='POST':return respond('405 Method Not Allowed',{'error':'post_required'})
        if env.get('HTTP_ORIGIN')!=origin:return respond('403 Forbidden',{'error':'origin_denied'})
        if env.get('CONTENT_TYPE','').split(';')[0]!='application/json':
            return respond('415 Unsupported Media Type',{'error':'json_required'})
        try:
            n=int(env.get('CONTENT_LENGTH','0'))
            if not 0<n<=2048:raise ValueError()
            raw=env['wsgi.input'].read(n)
            if len(raw)!=n:raise ValueError()
            from .stream_api import strict_json
            data=strict_json(raw)
            if not isinstance(data,dict):raise ValueError()
        except (ValueError,KeyError,TypeError,UnicodeError,RecursionError):
            return respond('400 Bad Request',{'error':'invalid_request'})
        try:
            if path=='/auth/logout':
                if data:raise AccountDenied('Invalid logout')
                accounts.logout(env)
                return respond('200 OK',{'signed_out':True},[('Set-Cookie',COOKIE+'=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0')])
            if path=='/auth/token':
                if data:raise AccountDenied('Invalid token request')
                return respond('200 OK',{'token':accounts.api_token(env),'expires_in':600})
            expected={'username','password'}|({'setup_token'} if path=='/auth/setup' else set())
            if set(data)!=expected:raise AccountDenied('Invalid fields')
            username=data['username']
            if not isinstance(username,str) or not USER.fullmatch(username):raise AccountDenied('Invalid account name')
            accounts.throttle(username)
            if path in ('/auth/register','/auth/setup'):
                accounts.register(username,data['password'],setup_token=data.get('setup_token'))
                return respond('201 Created',{'account_created':True})
            token=accounts.login(username,data['password'])
            return respond('200 OK',{'signed_in':True},[('Set-Cookie',COOKIE+'='+token+'; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=28800')])
        except RateLimited:return respond('429 Too Many Requests',{'error':'try_again_later'},[('Retry-After','60')])
        except AccountDenied:return respond('400 Bad Request' if path!='/auth/login' else '401 Unauthorized',{'error':'account_request_denied'})
    return application
