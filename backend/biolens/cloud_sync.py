"""Metadata/chat synchronization. File paths and artifacts never go to the cloud."""
import json
import asyncio
from . import cloud_client as cloud,store

async def flush():
    if not cloud.enabled():return
    for entry in store.rows('SELECT * FROM outbox ORDER BY rowid LIMIT 500'):
        data=json.loads(entry['payload'])
        await cloud.call('/chats/'+data.pop('chat_id')+'/messages','POST',data)
        store.execute('DELETE FROM outbox WHERE id=?',(entry['id'],))

async def projects():
    remote=await cloud.call('/projects')
    for p in remote:
        store.execute("INSERT INTO projects(id,name,path,created) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",(p['id'],p['name'],'',p['created']))

async def chats(project_id):
    for c in await cloud.call('/chats?project_id='+project_id):
        store.execute('INSERT INTO chats VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title',(c['id'],c['project_id'],c['title'],c['created']))

async def messages(chat_id):
    await flush()
    after=0
    while True:
        batch=await cloud.call('/chats/'+chat_id+'/messages?after='+str(after))
        for m in batch:
            store.execute('INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?)',(m['id'],chat_id,m['role'],m['content'],m['created']))
            after=m['seq']
        if len(batch)<500:break

async def finish_run(runner):
    await runner.run()
    try:await flush()
    except Exception:
        store.event(runner.run_id,'sync_warning',{'text':'聊天尚未同步，重新连接后打开聊天会自动重试。'})
