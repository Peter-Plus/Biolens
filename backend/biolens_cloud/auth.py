import hashlib,hmac,secrets,time,uuid
from collections import defaultdict,deque
from fastapi import HTTPException,Request
from . import db

_attempts=defaultdict(deque)
def limit(key,count,seconds):
    now=time.monotonic();q=_attempts[key]
    while q and q[0]<now-seconds:q.popleft()
    if len(q)>=count:raise HTTPException(429,'请求过于频繁，请稍后再试。')
    q.append(now)
    if len(_attempts)>10000:
        for k in list(_attempts):
            if not _attempts[k] or _attempts[k][-1]<now-3600:_attempts.pop(k,None)

def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    digest=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
    return salt+':'+digest

def password_ok(password,encoded):
    return hmac.compare_digest(password_hash(password,encoded.split(':')[0]),encoded)

def session(user):
    token=secrets.token_urlsafe(32);expires=time.time()+7*86400
    db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
    db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user['id'],expires))
    return {'token':token,'user':{'id':user['id'],'username':user['username']},'expires':expires}

def current_user(request:Request):
    token=request.headers.get('Authorization','').removeprefix('Bearer ')
    hashed=hashlib.sha256(token.encode()).hexdigest()
    result=db.rows('SELECT u.id,u.username FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.hash=? AND s.expires>?',(hashed,time.time()))
    if not result:raise HTTPException(401,'请重新登录 BioLens。')
    return result[0]

def client_ip(request):
    return request.headers.get('X-Real-IP',request.client.host if request.client else 'unknown')
