"""Browser session boundary, uploaded project storage and bounded execution queue."""
import asyncio
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Response
from . import cloud_client as cloud, store
from .account import Credentials
from .config import DATA_DIR
from .local import TEXT_SUFFIXES, SECRET_NAMES

ENABLED=os.getenv('BIOLENS_WEB')=='1'
COOKIE='biolens_session'
ORIGIN=os.getenv('BIOLENS_WEB_ORIGIN','https://biolens.worldlinesite.com')
router=APIRouter()
queue=asyncio.Semaphore(1)
file_locks={}

async def current(request):
    token=request.cookies.get(COOKIE)
    if not token:return None
    try:user=await cloud.call('/auth/me',token=token)
    except HTTPException as exc:
        if exc.status_code==401:return None
        raise
    return {'token':token,'user':user}

@router.get('/account')
def account():
    session=cloud.session()
    return {'enabled':True,'user':session['user'] if session else None,'server':ORIGIN,'web':True}

@router.post('/account/{action}')
async def authenticate(action:str,value:Credentials,response:Response,request:Request):
    if action not in {'login','register'}:raise HTTPException(404)
    result=await cloud.call('/auth/'+action,'POST',value.model_dump(),headers={'X-Real-IP':request.headers.get('x-real-ip',request.client.host if request.client else 'unknown')})
    scope=store.user_scope.set(result['user']['id'])
    try:store.init(reset_runs=False)
    finally:store.user_scope.reset(scope)
    response.set_cookie(COOKIE,result['token'],httponly=True,secure=True,samesite='strict',max_age=7*86400,path='/web-api')
    return {'enabled':True,'user':result['user'],'server':ORIGIN,'web':True}

@router.post('/account-logout')
async def logout(response:Response):
    from .api import RUNNERS
    if any(r.owner==store.user_scope.get() for r in RUNNERS.values()):raise HTTPException(409,'请等待任务完成或停止任务后退出。')
    if cloud.session():await cloud.call('/auth/logout','POST')
    response.delete_cookie(COOKIE,path='/web-api',secure=True,httponly=True,samesite='strict')
    return {'ok':True}

def project_directory(project_id):
    from .api import one
    one('SELECT id FROM projects WHERE id=?',(project_id,))
    base=DATA_DIR/'uploads'/store.user_scope.get()/project_id
    base.mkdir(parents=True,exist_ok=True)
    return base

def idle():
    from .api import RUNNERS
    if any(r.owner==store.user_scope.get() for r in RUNNERS.values()):raise HTTPException(409,'任务运行或排队期间不能修改资料。')

@router.get('/projects/{project_id}/files')
def files(project_id:str):
    base=project_directory(project_id)
    return [{'name':p.name,'bytes':p.stat().st_size} for p in sorted(base.iterdir()) if p.is_file() and not p.name.startswith('.')]

@router.put('/projects/{project_id}/files/{name}')
async def upload(project_id:str,name:str,request:Request):
    idle()
    if not re.fullmatch(r'[^/\\\x00-\x1f:]{1,180}',name) or name.startswith('.') or Path(name).suffix.lower() not in TEXT_SUFFIXES or SECRET_NAMES.search(name):raise HTTPException(400,'仅支持 CSV、TSV、PDF、MD、TXT，文件名不能包含路径或凭据名称。')
    base=project_directory(project_id)
    lock=file_locks.setdefault(store.user_scope.get(),asyncio.Lock())
    async with lock:
        target=base/name
        if target.exists():raise HTTPException(409,'同名文件已存在，请先删除旧文件。')
        used=sum(p.stat().st_size for p in base.parent.rglob('*') if p.is_file())
        if len(list(base.iterdir()))>=100:raise HTTPException(413,'每个项目最多 100 个文件。')
        temp=base/('.upload-'+store.uid());size=0
        try:
            with temp.open('xb') as output:
                async for chunk in request.stream():
                    size+=len(chunk)
                    if size>100*1024**2 or used+size>500*1024**2:raise HTTPException(413,'单文件上限 100 MB，每账号上传总量上限 500 MB。')
                    output.write(chunk)
            idle()
            temp.replace(target)
            store.execute('UPDATE projects SET path=? WHERE id=?',(str(base),project_id))
        finally:temp.unlink(missing_ok=True)
    return {'name':name,'bytes':size}

@router.delete('/projects/{project_id}/files/{name}')
def remove(project_id:str,name:str):
    idle();base=project_directory(project_id)
    target=(base/name).resolve()
    if target.parent!=base.resolve() or not target.is_file():raise HTTPException(404)
    target.unlink()
    return {'ok':True}

async def execute(runner):
    from . import cloud_sync
    store.event(runner.run_id,'status',{'text':'已进入云端任务队列，关闭网页不会中断任务。'})
    try:
        async with queue:
            runner.executing=True
            await cloud_sync.finish_run(runner)
    except asyncio.CancelledError:
        store.execute("UPDATE runs SET status='cancelled' WHERE id=?",(runner.run_id,))
        store.event(runner.run_id,'done',{'status':'cancelled'})
