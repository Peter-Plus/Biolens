import {ArrowDownToLine} from 'lucide-react';
import type {Artifact} from './api';

export function visibleArtifacts(items:Artifact[]){
 const reports=new Set(items.filter(a=>a.name==='report.html'||a.name==='report.pdf').map(a=>a.run_id));
 const unique=new Map<string,Artifact>();
 for(const a of items){
  if(a.kind==='json')continue;
  if(a.kind==='html' && a.name!=='report.html' && (reports.has(a.run_id)||a.name!=='analysis.html'))continue;
  unique.set(a.run_id+':'+a.name,a);
 }
 return [...unique.values()];
}

export default function ArtifactList({items,onPreview,onDownload}:{items:Artifact[];onPreview:(a:Artifact)=>void;onDownload:(a:Artifact)=>void}){
 const runs=[...new Set(items.map(a=>a.run_id))].reverse();
 const row=(a:Artifact)=><div className="artifact" key={a.id}><button onClick={()=>onPreview(a)}><span className="file-kind">{a.kind.toUpperCase()}</span><span>{a.name}</span></button><button className="icon-button" aria-label={'下载 '+a.name} onClick={()=>onDownload(a)}><ArrowDownToLine size={16}/></button></div>;
 return <div className="artifact-list">{runs.map((id,index)=>{
  const files=items.filter(a=>a.run_id===id);
  return <section className="artifact-run" key={id}>
   <h3>{runs.length>1?`第 ${runs.length-index} 次成果`:'本次成果'}</h3>
   {files.filter(a=>['html','pdf'].includes(a.kind)).map(row)}
   {(['png','svg','csv'] as const).map(kind=>{
    const group=files.filter(a=>a.kind===kind);
    return group.length>0&&<details className="artifact-group" key={kind}><summary>{kind==='png'?'PNG 图片':kind==='svg'?'SVG 矢量图':'分析数据'}<span>{group.length}</span></summary><p>{kind==='png'?'直接插入文档或演示文稿。':kind==='svg'?'放大不模糊，适合排版及矢量编辑。':'用于复核数值和进一步分析。'}</p>{group.map(row)}</details>;
   })}
  </section>;
 })}</div>;
}
