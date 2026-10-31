from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from . import cloud_client as cloud,store
router=APIRouter()
class Credentials(BaseModel):
    username:str=Field(min_length=3,max_length=32)
    password:str=Field(min_length=10,max_length=128)

@router.get('/account')
def account():
    current=cloud.session()
    return {'enabled':cloud.enabled(),'user':current.get('user') if current else None,'server':cloud.URL}

@router.post('/account/{action}')
async def authenticate(action:str,value:Credentials):
    if action not in {'register','login'}:raise HTTPException(404,'操作不存在。')
    from .api import RUNNERS
    if RUNNERS:raise HTTPException(409,'请先等待当前任务完成。')
    result=await cloud.call('/auth/'+action,'POST',value.model_dump())
    cloud.SESSION=result
    token=store.user_scope.set(result['user']['id'])
    try:store.init()
    finally:store.user_scope.reset(token)
    return {'enabled':True,'user':result['user'],'server':cloud.URL}

@router.post('/account-logout')
async def logout():
    from .api import RUNNERS
    if RUNNERS:raise HTTPException(409,'请先等待当前任务完成。')
    try:
        if cloud.SESSION:await cloud.call('/auth/logout','POST')
    except HTTPException:
        pass  # Offline logout must still clear local credentials.
    finally:cloud.SESSION=None
    return {'ok':True}
