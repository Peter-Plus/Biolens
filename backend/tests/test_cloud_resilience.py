import asyncio
import httpx
import pytest
from biolens import pubmed

@pytest.mark.asyncio
async def test_ncbi_block_page_uses_indexed_fallback(monkeypatch):
    calls=[]
    def respond(request):
        calls.append(str(request.url))
        if 'ncbi.nlm.nih.gov' in request.url.host:
            return httpx.Response(200,text='<html>blocked</html>')
        assert 'SRC:MED' in request.url.params['query']
        return httpx.Response(200,json={'hitCount':1,'resultList':{'result':[{'pmid':'12345678','title':'Evidence','abstractText':'Abstract'}]}})
    original=httpx.AsyncClient
    monkeypatch.setattr(pubmed.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(respond),**kw))
    result=await pubmed.search_pubmed('STAT1',2)
    assert len(calls)==2
    assert result['papers'][0]['pmid']=='12345678'
    assert result['source'].startswith('Europe PMC')

@pytest.mark.asyncio
async def test_five_model_slots_and_same_user_rejection(monkeypatch):
    from biolens_cloud import api
    from fastapi import HTTPException
    active=0;peak=0;entered=asyncio.Event();release=asyncio.Event()
    class Provider:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):
            nonlocal active,peak
            active+=1;peak=max(peak,active)
            if active==5:entered.set()
            await release.wait()
            active-=1
            return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':'ok'}}]})
    monkeypatch.setattr(api.httpx,'AsyncClient',lambda **kw:Provider())
    monkeypatch.setattr(api,'semaphore',asyncio.Semaphore(5))
    monkeypatch.setattr(api,'active_users',set())
    monkeypatch.setenv('BIOLENS_BASE_URL','https://provider.test/v1')
    monkeypatch.setenv('BIOLENS_API_KEY','fake-test-key')
    value=api.Inference(model='qwen3.7-flash',messages=[{'role':'user','content':'test'}])
    tasks=[asyncio.create_task(api.inference(value,{'id':str(i)})) for i in range(6)]
    try:
        await asyncio.wait_for(entered.wait(),3)
        with pytest.raises(HTTPException) as error:await api.inference(value,{'id':'0'})
        assert error.value.status_code==429
        assert peak==5 and not tasks[5].done()
    finally:
        release.set()
        await asyncio.gather(*tasks)
    assert peak==5 and not api.active_users
