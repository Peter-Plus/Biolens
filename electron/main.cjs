const {app, BrowserWindow, ipcMain, dialog, shell} = require('electron');
const {spawn} = require('node:child_process');
const {existsSync, readFileSync} = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const net = require('node:net');
let worker, endpoint, mainWindow;
const token = crypto.randomBytes(32).toString('hex');
const root = path.resolve(__dirname,'..');
async function freePort(){ return new Promise(resolve=>{const s=net.createServer();s.listen(0,'127.0.0.1',()=>{const p=s.address().port;s.close(()=>resolve(p));});}); }
async function startBackend(){
  const resource = app.isPackaged ? process.resourcesPath : root;
  let config={}; const configFile=path.join(root,'.local','dev.json');
  if(!app.isPackaged && existsSync(configFile)) config=JSON.parse(readFileSync(configFile,'utf8'));
  const python = process.env.BIOLENS_PYTHON || config.python || path.join(resource,'python','python.exe');
  const packagedPython = path.join(root,'runtime','python','python.exe');
  const executable=existsSync(python)?python:packagedPython;
  if(!existsSync(executable)) throw new Error('未找到Python运行环境。请运行 scripts/setup.ps1。');
  const port = await freePort(); endpoint=`http://127.0.0.1:${port}`;
  const pythonPaths=[path.join(resource,'backend')];
  if(!app.isPackaged) pythonPaths.push(path.join(root,'.local','pylibs'));
  worker=spawn(executable,['-m','biolens'],{windowsHide:true,stdio:['ignore','pipe','pipe'],env:{...process.env,
    BIOLENS_CLOUD_URL:process.env.BIOLENS_CLOUD_URL || (app.isPackaged?'https://biolens.worldlinesite.com':''),PYTHONPATH:pythonPaths.join(path.delimiter),PYTHONUTF8:'1',BIOLENS_DATA:process.env.BIOLENS_DATA || config.data || app.getPath('userData'),BIOLENS_PORT:String(port),BIOLENS_TOKEN:token,
    PLAYWRIGHT_BROWSERS_PATH:app.isPackaged?path.join(resource,'python','browsers'):(config.browsers||path.join(root,'.local','browsers'))}});
  worker.on('error',error=>dialog.showErrorBox('BioLens 后端启动失败',error.message));
  worker.stderr.on('data',data=>{if(process.env.BIOLENS_DEV) process.stderr.write(data);});
  let exited=false;worker.on('exit',()=>{exited=true;});
  for(let i=0;i<120;i++){
    if(exited) throw new Error('Python服务提前退出，请检查依赖是否完整。');
    try {const r=await fetch(endpoint+'/health',{headers:{Authorization:`Bearer ${token}`}});if(r.ok)return;}catch{}
    await new Promise(r=>setTimeout(r,500));
  }
  throw new Error('本地分析服务启动超时。');
}
app.whenReady().then(async()=>{
  try{
    await startBackend();
    ipcMain.handle('connection',()=>({url:endpoint,token}));
    ipcMain.handle('choose-directory',async()=>{const r=await dialog.showOpenDialog(mainWindow,{properties:['openDirectory']});return r.canceled?null:r.filePaths[0];});
    ipcMain.handle('external',async(_,url)=>{const u=new URL(url);if(u.protocol==='https:'||u.protocol==='http:')await shell.openExternal(url);});
    ipcMain.handle('save-artifact',async(_,id,name)=>{
      if(!/^[a-f0-9]{32}$/.test(id))throw new Error('Invalid artifact');
      const {canceled,filePath}=await dialog.showSaveDialog(mainWindow,{defaultPath:path.basename(name)});
      if(canceled)return false;
      const r=await fetch(`${endpoint}/artifacts/${id}`,{headers:{Authorization:`Bearer ${token}`}});
      if(!r.ok)throw new Error('下载失败');
      require('node:fs').writeFileSync(filePath,Buffer.from(await r.arrayBuffer()));return true;
    });
    mainWindow=new BrowserWindow({width:1380,height:900,minWidth:940,minHeight:650,show:!process.env.BIOLENS_SCREENSHOT,backgroundColor:'#ffffff',title:'BioLens',icon:path.join(app.isPackaged?process.resourcesPath:path.join(root,'assets'),'icon.png'),autoHideMenuBar:true,
      webPreferences:{preload:path.join(__dirname,'preload.cjs'),nodeIntegration:false,contextIsolation:true,sandbox:true}});
    mainWindow.webContents.setWindowOpenHandler(({url})=>{if(/^https?:/.test(url))shell.openExternal(url);return {action:'deny'};});
    mainWindow.webContents.on('will-navigate',(e,url)=>{if(!url.startsWith('http://127.0.0.1:5173')&&!url.startsWith('file://'))e.preventDefault();});
    if(process.env.BIOLENS_DEV)await mainWindow.loadURL('http://127.0.0.1:5173');else await mainWindow.loadFile(path.join(root,'dist','index.html'));
    if(process.env.BIOLENS_SCREENSHOT){setTimeout(async()=>{try{const image=await mainWindow.webContents.capturePage();require('node:fs').writeFileSync(process.env.BIOLENS_SCREENSHOT,image.toPNG());}finally{app.quit();}},4000);}
  }catch(error){dialog.showErrorBox('BioLens 无法启动',error.message);app.quit();}
});
app.on('window-all-closed',()=>app.quit());
app.on('before-quit',()=>{worker?.kill();});
