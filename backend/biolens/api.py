import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from . import store, web
from .schemas import ProjectIn, ChatIn, TurnIn, SettingsIn, LocalPathIn
from .config import public_settings, save_settings, read_settings, ARTIFACT_DIR
from .agent import Runner, completion
from . import cloud_client as cloud, cloud_sync
from .account import router as account_router
from .models import MODELS, DEFAULT_MODEL, select_model

RUNNERS = {}
TASKS = {}


@asynccontextmanager
async def lifespan(app):
    store.init()
    if web.ENABLED:
        for directory in (store.DATA_DIR/'accounts').glob('*'):
            if directory.is_dir():
                token=store.user_scope.set(directory.name)
                try:store.init()
                finally:store.user_scope.reset(token)
    yield
    for task in list(TASKS.values()):
        task.cancel()


app = FastAPI(title="BioLens", lifespan=lifespan)
app.include_router(web.router if web.ENABLED else account_router)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "null"], allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "Authorization"])


@app.middleware("http")
async def authentication(request: Request, call_next):
    token = os.getenv("BIOLENS_TOKEN", "")
    if request.method != "OPTIONS" and token:
        provided = request.headers.get("Authorization", "").removeprefix("Bearer ")
        # Query capability is needed for browser downloads/iframes/EventSource.
        if provided != token and request.query_params.get("token") != token:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "未授权的本地请求。"}, status_code=401)
    if web.ENABLED:
        from fastapi.responses import JSONResponse
        if request.method not in {'GET','HEAD','OPTIONS'} and request.headers.get('origin')!=web.ORIGIN:
            return JSONResponse({'detail':'请求来源不匹配。'},status_code=403)
        try:current=await web.current(request)
        except HTTPException as exc:return JSONResponse({'detail':exc.detail},status_code=exc.status_code)
    else:current=cloud.SESSION
    if cloud.enabled() and request.url.path.removeprefix(request.scope.get('root_path','')) not in {'/health','/account','/account/login','/account/register','/account-logout'} and not current:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail':'请先登录 BioLens。'},status_code=401)
    scope=store.user_scope.set(current['user']['id'] if current else '')
    session_scope=cloud.context.set(current)
    try:
        response=await call_next(request)
        if web.ENABLED:
            response.headers['Cache-Control']='no-store'
            response.headers['X-Content-Type-Options']='nosniff'
        return response
    finally:
        store.user_scope.reset(scope)
        cloud.context.reset(session_scope)


def one(sql, args):
    found = store.rows(sql, args)
    if not found:
        raise HTTPException(404, "记录不存在。")
    return found[0]


@app.get("/health")
def health():
    return {"ok": True, "version": "0.3.0"}


@app.get("/settings")
def settings():
    if cloud.enabled():return {'base_url':cloud.URL,'model':DEFAULT_MODEL,'has_key':True,'managed':True}
    return public_settings()


@app.get("/models")
async def models():
    if cloud.enabled():return await cloud.call("/models")
    return {"models": MODELS, "default_model": DEFAULT_MODEL}


@app.post("/settings")
def update_settings(value: SettingsIn):
    if cloud.enabled():raise HTTPException(403,"模型配置由服务端管理。")
    from urllib.parse import urlparse
    parsed = urlparse(value.base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "请输入有效的API基础地址，例如 https://provider.example/v1。")
    save_settings(value.model_dump(exclude_none=True))
    return public_settings()


@app.post("/settings/test")
async def test_settings(model: str | None = None):
    try:
        result = await completion([{"role": "user", "content": "只回答：连接成功"}], model=select_model(model))
        return {"ok": True, "text": result.get("content", "")}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.get("/projects")
async def projects():
    if cloud.enabled():await cloud_sync.projects()
    items=store.rows("SELECT * FROM projects ORDER BY created DESC")
    if web.ENABLED:
        for item in items:item['path']='云端项目文件' if item['path'] else ''
    return items


@app.post("/projects")
async def create_project(value: ProjectIn):
    if web.ENABLED and value.path:raise HTTPException(400,"网页版请上传文件，不接受服务器路径。")
    if value.path and not Path(value.path).is_dir():
        raise HTTPException(400, "所选目录不存在。")
    item = {"id": store.uid(), "name": value.name.strip(), "path": str(Path(value.path).resolve()) if value.path else "", "created": store.now()}
    if cloud.enabled():await cloud.call('/projects','POST',{k:v for k,v in item.items() if k!='path'})
    store.execute("INSERT INTO projects VALUES (?,?,?,?)", tuple(item.values()))
    return item


@app.post('/projects/{project_id}/local-path')
def bind_local_path(project_id: str, value: LocalPathIn):
    if web.ENABLED:raise HTTPException(403,'网页版请使用文件上传。')
    if RUNNERS:raise HTTPException(409,'请先等待任务完成。')
    item=one('SELECT * FROM projects WHERE id=?',(project_id,))
    if not Path(value.path).is_dir():raise HTTPException(400,'所选目录不存在。')
    path=str(Path(value.path).resolve())
    store.execute('UPDATE projects SET path=? WHERE id=?',(path,project_id))
    return {**item,'path':path}


@app.get("/chats")
async def chats(project_id: str):
    if cloud.enabled():await cloud_sync.chats(project_id)
    return store.rows("SELECT * FROM chats WHERE project_id=? ORDER BY created DESC", (project_id,))


@app.post("/chats")
async def create_chat(value: ChatIn):
    one("SELECT * FROM projects WHERE id=?", (value.project_id,))
    item = {"id": store.uid(), "project_id": value.project_id, "title": "新聊天", "created": store.now()}
    if cloud.enabled():await cloud.call('/chats','POST',item)
    store.execute("INSERT INTO chats VALUES (?,?,?,?)", tuple(item.values()))
    return item


@app.get("/chats/{chat_id}")
async def chat(chat_id: str):
    if cloud.enabled():await cloud_sync.messages(chat_id)
    item = one("SELECT * FROM chats WHERE id=?", (chat_id,))
    return {**item, "messages": store.rows("SELECT * FROM messages WHERE chat_id=? ORDER BY rowid", (chat_id,)),
            "artifacts": store.rows("SELECT id,name,kind,run_id,created FROM artifacts WHERE chat_id=? ORDER BY rowid", (chat_id,)),
            "runs": store.rows("SELECT id,status,request FROM runs WHERE chat_id=? ORDER BY rowid DESC", (chat_id,))}


@app.post("/chats/{chat_id}/turns")
async def turn(chat_id: str, request: TurnIn):
    try:
        request = request.model_copy(update={"model": select_model(request.model)})
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    item = one("SELECT * FROM chats WHERE id=?", (chat_id,))
    if store.rows("SELECT id FROM runs WHERE chat_id=? AND status='running'", (chat_id,)):
        raise HTTPException(409, "当前聊天正在运行，请先停止或等待完成。")
    project = one("SELECT * FROM projects WHERE id=?", (item["project_id"],))
    if request.local and not project["path"]:
        raise HTTPException(400, "请先创建一个已选择本地目录的项目，或关闭本地读取。")
    if cloud.enabled():
        if any(getattr(r,'owner','')==store.user_scope.get() for r in RUNNERS.values()):raise HTTPException(409,'此账号已有任务运行或排队，请稍后重试。')
        await cloud_sync.messages(chat_id)
    if web.ENABLED and any(r.owner==store.user_scope.get() for r in RUNNERS.values()):
        raise HTTPException(409,'此账号已有任务运行或排队。')
    run_id = store.uid()
    store.message(chat_id, "user", request.prompt)
    if item["title"] == "新聊天":
        store.execute("UPDATE chats SET title=? WHERE id=?", (request.prompt[:28], chat_id))
    store.execute("INSERT INTO runs VALUES (?,?,?,?,?)", (run_id, chat_id, request.model_dump_json(), "running", store.now()))
    runner = Runner(run_id, chat_id, project, request)
    runner.owner=store.user_scope.get()
    RUNNERS[run_id] = runner
    task = asyncio.create_task(web.execute(runner) if web.ENABLED else cloud_sync.finish_run(runner) if cloud.enabled() else runner.run())
    TASKS[run_id] = task
    task.add_done_callback(lambda _: (TASKS.pop(run_id, None), RUNNERS.pop(run_id, None)))
    return {"run_id": run_id}


@app.get("/runs/{run_id}/events")
async def events(run_id: str, request: Request, after: int = 0):
    one("SELECT * FROM runs WHERE id=?", (run_id,))
    async def stream():
        cursor = max(after, int(request.headers.get("last-event-id", "0")))
        while True:
            if await request.is_disconnected():
                return
            entries = store.rows("SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id", (run_id, cursor))
            for entry in entries:
                cursor = entry["id"]
                yield f'id: {cursor}\ndata: {json.dumps({"kind": entry["kind"], "payload": json.loads(entry["payload"])}, ensure_ascii=False)}\n\n'
            status = one("SELECT status FROM runs WHERE id=?", (run_id,))["status"]
            if status != "running":
                yield 'data: ' + json.dumps({"kind": "closed", "payload": {"status": status}}) + '\n\n'
                return
            yield ": heartbeat\n\n"
            await asyncio.sleep(.35)
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/runs/{run_id}/trace")
def trace(run_id: str):
    return [{**row, "payload": json.loads(row["payload"])} for row in store.rows("SELECT * FROM events WHERE run_id=? ORDER BY id", (run_id,))]


@app.post("/runs/{run_id}/cancel")
async def cancel(run_id: str):
    one("SELECT id FROM runs WHERE id=?", (run_id,))
    if run_id in RUNNERS:
        RUNNERS[run_id].cancelled = True
        if web.ENABLED and getattr(RUNNERS[run_id],'executing',False):
            store.event(run_id,'status',{'text':'正在停止，等待当前步骤收尾。'})
        else:TASKS[run_id].cancel()
    return {"ok": True}


@app.get("/artifacts/{artifact_id}")
def artifact(artifact_id: str, download: bool = False):
    item = one("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
    path = Path(item["path"]).resolve()
    if not path.is_relative_to(ARTIFACT_DIR) or not path.is_file():
        raise HTTPException(404, "文件不存在。")
    response = FileResponse(path, filename=item["name"] if download else None)
    if path.suffix == ".html":
        response.headers["Content-Security-Policy"] = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none';"
    return response


def pdf_path(artifact_id):
    item = one("SELECT * FROM artifacts WHERE id=?", (artifact_id,))
    path = Path(item["path"]).resolve()
    if not path.is_relative_to(ARTIFACT_DIR) or not path.is_file() or path.suffix != ".pdf":
        raise HTTPException(404, "PDF不存在。")
    return path


@app.get("/artifacts/{artifact_id}/preview")
def pdf_preview(artifact_id: str, request: Request):
    import pymupdf
    from html import escape
    from urllib.parse import quote
    with pymupdf.open(pdf_path(artifact_id)) as doc:
        count = min(len(doc), 100)
    token = quote(request.query_params.get("token", ""), safe="")
    pages = ''.join(f'<figure><img loading="lazy" src="{request.scope.get("root_path", "")}/artifacts/{artifact_id}/pages/{i}?token={token}" alt="第{i+1}页"><figcaption>{i+1} / {count}</figcaption></figure>' for i in range(count))
    return HTMLResponse('<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#e9eeeb;font:12px Arial;color:#65736b}figure{margin:12px 10px}img{width:100%;display:block;background:white}figcaption{text-align:center;padding:8px}</style></head><body>'+pages+'</body></html>', headers={"Content-Security-Policy":"default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"})


@app.get("/artifacts/{artifact_id}/pages/{page}")
def pdf_page(artifact_id: str, page: int):
    import pymupdf
    with pymupdf.open(pdf_path(artifact_id)) as doc:
        if page < 0 or page >= min(len(doc), 100):
            raise HTTPException(404, "页码不存在。")
        png = doc[page].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).tobytes("png")
    return Response(content=png, media_type="image/png")
