"""Authenticated cloud transport. Session secrets never enter the renderer."""
import os
from contextvars import ContextVar
import httpx
from fastapi import HTTPException

URL=os.environ.get('BIOLENS_CLOUD_URL','').rstrip('/')
SESSION=None
context=ContextVar('cloud_session',default=None)

def enabled():return bool(URL)
def session():return context.get() or SESSION

async def call(path,method='GET',payload=None,token=None,headers=None):
    auth=token or (session() or {}).get('token')
    request_headers=dict(headers or {})
    if auth:request_headers['Authorization']='Bearer '+auth
    async with httpx.AsyncClient(timeout=httpx.Timeout(150,connect=20)) as client:
        try:r=await client.request(method,URL+path,json=payload,headers=request_headers)
        except httpx.RequestError as exc:raise HTTPException(503,'无法连接 BioLens 云端，请检查网络。') from exc
    if not r.is_success:
        try:detail=r.json().get('detail','云端请求失败。')
        except ValueError:detail='云端请求失败。'
        raise HTTPException(r.status_code,detail if isinstance(detail,str) else '输入格式不正确，请检查用户名和密码。')
    return r.json()
