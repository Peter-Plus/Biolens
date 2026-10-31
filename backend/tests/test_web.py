import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from biolens import api,web,store,cloud_client as cloud

@pytest.fixture
def browser(monkeypatch,tmp_path):
    monkeypatch.setattr(web,'ENABLED',True)
    monkeypatch.setattr(web,'DATA_DIR',tmp_path)
    monkeypatch.setattr(store,'DATA_DIR',tmp_path)
    monkeypatch.setattr(cloud,'URL','https://cloud.test')
    monkeypatch.setattr(cloud,'SESSION',None)
    monkeypatch.setenv('BIOLENS_TOKEN','')
    routes=api.app.router.routes[:]
    api.app.router.routes[:]=[r for r in routes if type(r).__name__!='_IncludedRouter']
    api.app.include_router(web.router)
    async def transport(path,method='GET',payload=None,token=None,headers=None):
        if path=='/auth/me':
            if token not in {'alice','bravo'}:raise HTTPException(401)
            return {'id':token,'username':token}
        if path.startswith('/auth/'):
            return {'token':payload['username'],'user':{'id':payload['username'],'username':payload['username']}}
        if path=='/projects' and method=='GET':return []
        return payload or []
    monkeypatch.setattr(cloud,'call',transport)
    with TestClient(api.app,base_url=web.ORIGIN,root_path='/web-api',headers={'Origin':web.ORIGIN}) as client:
        yield client
    api.app.router.routes[:]=routes

def test_web_auth_upload_isolation_and_paths(browser):
    b=browser
    assert b.get('/web-api/projects').status_code==401
    r=b.post('/web-api/account/login',json={'username':'alice','password':'test-password-2026'})
    assert r.status_code==200
    assert 'HttpOnly' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
    assert b.post('/web-api/projects',json={'name':'unsafe','path':'/etc'}).status_code==400
    p=b.post('/web-api/projects',json={'name':'research','path':''}).json()['id']
    endpoint='/web-api/projects/'+p+'/files'
    assert b.put(endpoint+'/expression.csv',content=b'gene,s1\nSTAT1,1').status_code==200
    assert b.put(endpoint+'/expression.csv',content=b'overwrite').status_code==409
    assert b.put(endpoint+'/key.txt',content=b'secret').status_code==400
    assert b.put(endpoint+'/code.py',content=b'print(1)').status_code==400
    assert b.post('/web-api/projects/'+p+'/local-path',json={'path':'/etc'}).status_code==403
    assert b.get(endpoint).json()[0]['name']=='expression.csv'
    assert b.get('/web-api/projects').json()[0]['path']=='云端项目文件'
    assert b.delete(endpoint+'/expression.csv',headers={'Origin':'https://evil.test'}).status_code==403
    b.post('/web-api/account/login',json={'username':'bravo','password':'test-password-2026'})
    assert b.get(endpoint).status_code==404
    assert b.get('/web-api/projects').json()==[]
    assert b.post('/web-api/runs/unknown/cancel').status_code==404
    b.post('/web-api/account/login',json={'username':'alice','password':'test-password-2026'})
    assert b.delete(endpoint+'/expression.csv').status_code==200
    assert b.get(endpoint).json()==[]


@pytest.mark.asyncio
async def test_web_queue_serializes_and_cancels_waiting_job(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from biolens import cloud_sync
    entered=asyncio.Event();release=asyncio.Event();active=0;peak=0;events=[]
    async def finish(runner):
        nonlocal active,peak
        active+=1;peak=max(active,peak);entered.set()
        await release.wait();active-=1
    monkeypatch.setattr(web,'queue',asyncio.Semaphore(1))
    monkeypatch.setattr(cloud_sync,'finish_run',finish)
    monkeypatch.setattr(store,'event',lambda *args:events.append(args))
    monkeypatch.setattr(store,'execute',lambda *args:None)
    first=asyncio.create_task(web.execute(SimpleNamespace(run_id='first')))
    await entered.wait()
    second=asyncio.create_task(web.execute(SimpleNamespace(run_id='second')))
    await asyncio.sleep(0)
    second.cancel();await second
    assert any(e[0]=='second' and e[1]=='done' for e in events)
    release.set();await first
    assert peak==1
