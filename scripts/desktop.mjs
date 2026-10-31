import { spawn } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const vite = spawn(process.execPath, ['node_modules/vite/bin/vite.js','--host','127.0.0.1'], {stdio:'inherit',windowsHide:true});
let electron;
for(let i=0;i<80;i++) { try {await fetch('http://127.0.0.1:5173');break;} catch {await new Promise(r=>setTimeout(r,250));} }
electron = spawn(require('electron'), ['.'], {stdio:'inherit',windowsHide:true,env:{...process.env,BIOLENS_DEV:'1'}});
electron.on('exit',()=>vite.kill());
process.on('SIGINT',()=>{electron?.kill();vite.kill();});
