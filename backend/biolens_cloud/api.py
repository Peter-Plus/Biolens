import asyncio,json,os,sqlite3,time,uuid
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI,Depends,HTTPException,Request
from fastapi.responses import HTMLResponse,JSONResponse
from pydantic import BaseModel,Field,field_validator
from typing import Literal
from . import db,auth
from biolens.models import MODELS,DEFAULT_MODEL,select_model
from biolens.pubmed import search_pubmed

@asynccontextmanager
async def lifespan(app):
    db.init();yield
app=FastAPI(title='BioLens Cloud',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
semaphore=asyncio.Semaphore(5)
active_users=set()
search_lock=asyncio.Lock()

@app.middleware('http')
async def request_limits(request:Request,call_next):
    try:
        if int(request.headers.get('content-length','0'))>2_000_000:return JSONResponse({'detail':'请求过大。'},status_code=413)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        return response
    except ValueError:return JSONResponse({'detail':'请求无效。'},status_code=400)

class Credentials(BaseModel):
    username:str=Field(pattern=r'^[A-Za-z0-9_]{3,32}$')
    password:str=Field(min_length=10,max_length=128)
    @field_validator('username')
    @classmethod
    def normalize(cls,value):return value.lower()

class Project(BaseModel):
    id:str=Field(pattern=r'^[a-f0-9]{32}$')
    name:str=Field(min_length=1,max_length=100)
    created:str=Field(max_length=64)
class Chat(BaseModel):
    id:str=Field(pattern=r'^[a-f0-9]{32}$')
    project_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    title:str=Field(min_length=1,max_length=100)
    created:str=Field(max_length=64)
class Message(BaseModel):
    id:str=Field(pattern=r'^[a-f0-9]{32}$')
    role:Literal['user','assistant']
    content:str=Field(max_length=200000)
    created:str=Field(max_length=64)
class Inference(BaseModel):
    model:str
    messages:list[dict]=Field(min_length=1,max_length=80)
    tools:list[dict]|None=Field(default=None,max_length=24)
class Search(BaseModel):
    query:str=Field(min_length=1,max_length=1500)
    limit:int=Field(default=5,ge=1,le=10)

def owned(table,id,user):
    result=db.rows(f'SELECT * FROM {table} WHERE id=? AND user_id=?',(id,user['id']))
    if not result:raise HTTPException(404,'记录不存在。')
    return result[0]

@app.get('/',response_class=HTMLResponse)
def home():
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>BioLens</title><body style="font:18px/1.8 sans-serif;max-width:700px;margin:12vh auto;padding:24px;color:#24534f"><h1>BioLens</h1><p>生物信息学分析与可视化工作区</p><p>云端账号服务已上线。请在 Windows 客户端中注册或登录；项目文件读取、数据计算和报告生成在你的电脑上执行。</p></body></html>'
@app.get('/health')
def health():return {'ok':True,'service':'biolens-cloud','version':'0.2.0'}
@app.post('/auth/register')
def register(value:Credentials,request:Request):
    auth.limit('register:'+auth.client_ip(request),5,3600)
    user={'id':uuid.uuid4().hex,'username':value.username}
    try:db.execute('INSERT INTO users VALUES(?,?,?,?)',(user['id'],value.username,auth.password_hash(value.password),time.time()))
    except sqlite3.IntegrityError:raise HTTPException(409,'该用户名已被使用。')
    return auth.session(user)
@app.post('/auth/login')
def login(value:Credentials,request:Request):
    auth.limit('login:'+auth.client_ip(request),15,300)
    result=db.rows('SELECT * FROM users WHERE username=?',(value.username,))
    # Equal-cost hashing for unknown accounts.
    encoded=result[0]['password'] if result else auth.password_hash('unavailable-account')
    if not result or not auth.password_ok(value.password,encoded):raise HTTPException(401,'用户名或密码不正确。')
    return auth.session(result[0])
@app.get('/auth/me')
def me(user=Depends(auth.current_user)):return user
@app.post('/auth/logout')
def logout(request:Request,user=Depends(auth.current_user)):
    import hashlib
    token=request.headers['Authorization'].removeprefix('Bearer ')
    db.execute('DELETE FROM sessions WHERE hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
    return {'ok':True}
@app.get('/models')
def models(user=Depends(auth.current_user)):return {'models':MODELS,'default_model':DEFAULT_MODEL}
@app.get('/projects')
def projects(user=Depends(auth.current_user)):
    return db.rows('SELECT id,name,created FROM projects WHERE user_id=? ORDER BY created DESC',(user['id'],))
@app.post('/projects')
def project(value:Project,user=Depends(auth.current_user)):
    existing=db.rows('SELECT user_id FROM projects WHERE id=?',(value.id,))
    if existing and existing[0]['user_id']!=user['id']:raise HTTPException(404,'记录不存在。')
    db.execute('INSERT INTO projects VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name',(value.id,user['id'],value.name,value.created))
    return value
@app.get('/chats')
def chats(project_id:str,user=Depends(auth.current_user)):
    owned('projects',project_id,user)
    return db.rows('SELECT id,project_id,title,created FROM chats WHERE project_id=? AND user_id=? ORDER BY created DESC',(project_id,user['id']))
@app.post('/chats')
def chat(value:Chat,user=Depends(auth.current_user)):
    owned('projects',value.project_id,user)
    existing=db.rows('SELECT user_id FROM chats WHERE id=?',(value.id,))
    if existing and existing[0]['user_id']!=user['id']:raise HTTPException(404,'记录不存在。')
    db.execute('INSERT INTO chats VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=CASE WHEN excluded.title=\'新聊天\' THEN chats.title ELSE excluded.title END',(value.id,value.project_id,user['id'],value.title,value.created))
    return value
@app.get('/chats/{chat_id}/messages')
def messages(chat_id:str,after:int=0,user=Depends(auth.current_user)):
    owned('chats',chat_id,user)
    return db.rows('SELECT seq,id,role,content,created FROM messages WHERE chat_id=? AND user_id=? AND seq>? ORDER BY seq LIMIT 500',(chat_id,user['id'],after))
@app.post('/chats/{chat_id}/messages')
def message(chat_id:str,value:Message,user=Depends(auth.current_user)):
    owned('chats',chat_id,user)
    existing=db.rows('SELECT chat_id,user_id FROM messages WHERE id=?',(value.id,))
    if existing and (existing[0]['user_id']!=user['id'] or existing[0]['chat_id']!=chat_id):raise HTTPException(404,'记录不存在。')
    db.execute('INSERT OR IGNORE INTO messages(id,chat_id,user_id,role,content,created) VALUES(?,?,?,?,?,?)',(value.id,chat_id,user['id'],value.role,value.content,value.created))
    if value.role=='user':db.execute("UPDATE chats SET title=? WHERE id=? AND title='新聊天'",(value.content[:28],chat_id))
    return {'ok':True}
@app.post('/inference')
async def inference(value:Inference,user=Depends(auth.current_user)):
    try:model=select_model(value.model)
    except ValueError as e:raise HTTPException(400,str(e))
    auth.limit('inference:'+user['id'],120,60)
    if user['id'] in active_users:raise HTTPException(429,'这个账号已有模型请求运行，请稍后重试。')
    active_users.add(user['id'])
    try:
        async with semaphore:
            body={'model':model,'messages':value.messages,'temperature':.2,'enable_thinking':False,'max_tokens':8192}
            if value.tools:body['tools']=value.tools
            async with httpx.AsyncClient(timeout=httpx.Timeout(120,connect=20)) as client:
                r=await client.post(os.environ['BIOLENS_BASE_URL'].rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+os.environ['BIOLENS_API_KEY']},json=body)
            if not r.is_success:raise HTTPException(502,f'模型服务返回HTTP {r.status_code}。')
            return r.json()['choices'][0]['message']
    finally:active_users.discard(user['id'])
@app.post('/search/pubmed')
async def pubmed(value:Search,user=Depends(auth.current_user)):
    auth.limit('search:'+user['id'],30,60)
    try:
        async with search_lock:
            try:return await search_pubmed(value.query,value.limit)
            finally:await asyncio.sleep(.4)
    except (httpx.HTTPError,ValueError,KeyError):raise HTTPException(502,'文献检索服务暂不可用，请稍后重试。')
