import asyncio
import json
import httpx
import pytest
from biolens import agent
from biolens.schemas import SettingsIn


def test_settings_no_longer_require_model():
    assert SettingsIn(base_url='https://example.test/v1').model is None


def test_server_catalog_and_reject_custom_model(monkeypatch):
    from fastapi.testclient import TestClient
    from biolens.api import app
    from biolens import store
    monkeypatch.setenv('BIOLENS_TOKEN','')
    with TestClient(app) as client:
        catalog=client.get('/models').json()
        assert len(catalog['models'])==6
        assert catalog['models'][1]['id']=='qwen3.7-flash'
        assert catalog['models'][-1]['id']=='qwen3.8-max'
        project=client.post('/projects',json={'name':'catalog'}).json()
        chat=client.post('/chats',json={'project_id':project['id']}).json()
        response=client.post('/chats/'+chat['id']+'/turns',json={'prompt':'hello','model':'not-authorized'})
        assert response.status_code==400
        assert not store.rows('SELECT * FROM messages WHERE chat_id=?',(chat['id'],))
        assert client.post('/settings/test?model=not-authorized').status_code==400


@pytest.mark.asyncio
async def test_concurrent_model_selection_is_request_scoped(monkeypatch):
    monkeypatch.setattr(agent, 'read_settings', lambda: {'base_url':'https://example.test/v1','model':'default','api_key':'test'})
    sent=[]
    async def handle(request):
        body=json.loads(request.content)
        sent.append(body['model'])
        return httpx.Response(200,json={'choices':[{'message':{'content':'NO'}}]})
    client_type=httpx.AsyncClient
    monkeypatch.setattr(agent.httpx,'AsyncClient',lambda **kw:client_type(transport=httpx.MockTransport(handle),**kw))
    await asyncio.gather(agent.completion([{'role':'user','content':'hello'}],model='model-a'),agent.completion([{'role':'user','content':'hello'}],model='model-b'))
    assert sorted(sent)==['model-a','model-b']
    await agent.explicit_search_request('解释这个概念',model='classifier-model')
    assert sent[-1]=='classifier-model'
    await agent.completion([{'role':'user','content':'hello'}])
    assert sent[-1]=='default'
