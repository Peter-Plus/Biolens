declare global {interface Window {biolens?:{connection:()=>Promise<{url:string;token:string}>;chooseDirectory:()=>Promise<string|null>;openExternal:(url:string)=>Promise<void>;saveArtifact:(id:string,name:string)=>Promise<boolean>}}}
export const isWeb=!window.biolens && location.port!=='5173';
let connection={url:isWeb?'/web-api':'http://127.0.0.1:8765',token:''};
export async function connect(){if(window.biolens)connection=await window.biolens.connection();}
export async function api<T=any>(path:string,method='GET',body?:unknown):Promise<T>{
 const r=await fetch(connection.url+path,{method,headers:{'Content-Type':'application/json',Authorization:`Bearer ${connection.token}`},body:body===undefined?undefined:JSON.stringify(body)});
 if(!r.ok){let v;try{v=await r.json();}catch{} throw new Error(typeof v?.detail==='string'?v.detail:`请求失败 (${r.status})`);}
 return r.json();
}
export function url(path:string){return connection.url+path+(path.includes('?')?'&':'?')+'token='+encodeURIComponent(connection.token);}
export type Project={id:string;name:string;path:string};
export type Chat={id:string;title:string;project_id:string};
export type Message={id:string;role:string;content:string};
export type Artifact={id:string;name:string;kind:string;run_id:string};
export type Trace={kind:string;payload:any};

export async function uploadFile(projectId:string,file:File){
 const r=await fetch(connection.url+'/projects/'+projectId+'/files/'+encodeURIComponent(file.name),{method:'PUT',headers:{'Content-Type':'application/octet-stream'},body:file});
 if(!r.ok){let detail='上传失败 ('+r.status+')';try{detail=(await r.json()).detail||detail;}catch{}throw new Error(detail);}
 return r.json();
}
