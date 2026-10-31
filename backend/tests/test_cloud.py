import uuid
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from biolens_cloud.api import app as server
from biolens_cloud import auth,db

@pytest.fixture
def remote(monkeypatch,tmp_path):
    monkeypatch.setenv('BIOLENS_CLOUD_DATA',str(tmp_path/'server'))
    auth._attempts.clear()
    with TestClient(server) as client:yield client

def signup(client,name):
    r=client.post('/auth/register',json={'username':name,'password':'Strong-test-pass-2026'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']},r.json()

def test_cloud_auth_ownership_and_idempotency(remote):
    a,account=signup(remote,'alice');b,_=signup(remote,'bravo')
    assert 'Strong-test' not in db.rows('SELECT password FROM users')[0]['password']
    p={'id':uuid.uuid4().hex,'name':'private project','created':'2026-10-31'}
    assert remote.post('/projects',headers=a,json=p).status_code==200
    assert remote.get('/projects',headers=b).json()==[]
    assert remote.post('/projects',headers=b,json=p).status_code==404
    c={'id':uuid.uuid4().hex,'project_id':p['id'],'title':'新聊天','created':'2026-10-31'}
    remote.post('/chats',headers=a,json=c)
    m={'id':uuid.uuid4().hex,'role':'user','content':'private text','created':'2026-10-31'}
    for _ in range(2):assert remote.post('/chats/'+c['id']+'/messages',headers=a,json=m).status_code==200
    assert len(remote.get('/chats/'+c['id']+'/messages',headers=a).json())==1
    assert remote.get('/chats/'+c['id']+'/messages',headers=b).status_code==404
    assert remote.post('/chats/'+c['id']+'/messages',headers=b,json=m).status_code==404
    assert remote.get('/models').status_code==401
    assert remote.post('/inference',headers=a,json={'model':'unlisted','messages':[{'role':'user','content':'hi'}]}).status_code==400
    remote.post('/auth/logout',headers=a)
    assert remote.get('/auth/me',headers=a).status_code==401

def test_local_cloud_accounts_keep_paths_and_artifacts_local(remote,monkeypatch,tmp_path):
    from biolens import cloud_client as cloud,store
    from biolens.api import app as local
    monkeypatch.setattr(cloud,'URL','https://cloud.test')
    monkeypatch.setattr(cloud,'SESSION',None)
    monkeypatch.setenv('BIOLENS_TOKEN','')
    monkeypatch.setattr(store,'DATA_DIR',tmp_path/'device-a')
    async def transport(path,method='GET',payload=None,token=None):
        session=cloud.session() or {}
        value=remote.request(method,path,json=payload,headers={'Authorization':'Bearer '+(token or session.get('token',''))})
        if not value.is_success:raise HTTPException(value.status_code,value.json().get('detail'))
        return value.json()
    monkeypatch.setattr(cloud,'call',transport)
    with TestClient(local) as client:
        assert client.get('/projects').status_code==401
        reg=client.post('/account/register',json={'username':'local_a','password':'Strong-test-pass-2026'}).json()
        user_a=reg['user']['id']
        p=client.post('/projects',json={'name':'same account','path':str(tmp_path)}).json()
        c=client.post('/chats',json={'project_id':p['id']}).json()
        scope=store.user_scope.set(user_a)
        try:store.message(c['id'],'user','hello from device a')
        finally:store.user_scope.reset(scope)
        assert client.get('/chats/'+c['id']).json()['messages'][0]['content']=='hello from device a'
        assert 'path' not in db.rows('SELECT * FROM projects')[0]
        client.post('/account-logout')
        client.post('/account/register',json={'username':'local_b','password':'Strong-test-pass-2026'})
        assert client.get('/projects').json()==[]
        assert client.get('/chats/'+c['id']).status_code==404
        client.post('/account-logout')
        monkeypatch.setattr(store,'DATA_DIR',tmp_path/'device-b')
        client.post('/account/login',json={'username':'local_a','password':'Strong-test-pass-2026'})
        imported=client.get('/projects').json()
        assert imported[0]['path']==''
        client.get('/chats?project_id='+p['id'])
        assert client.get('/chats/'+c['id']).json()['messages'][0]['content']=='hello from device a'
        assert client.post('/projects/'+p['id']+'/local-path',json={'path':str(tmp_path)}).status_code==200
