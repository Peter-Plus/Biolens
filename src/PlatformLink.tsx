import {Download,ExternalLink} from 'lucide-react';
import {isWeb} from './api';

export default function PlatformLink(){
 const href=isWeb?'https://github.com/Peter-Plus/Biolens/releases/latest':'https://biolens.worldlinesite.com/';
 return <a className="platform-link" href={href} target="_blank" rel="noopener noreferrer" title={isWeb?'打开最新 Windows 客户端下载页':'在默认浏览器打开 BioLens'} onClick={event=>{if(window.biolens){event.preventDefault();void window.biolens.openExternal(href);}}}>
  {isWeb?<Download size={16}/>:<ExternalLink size={16}/>}<span>{isWeb?'下载客户端':'打开网页版'}</span>
 </a>;
}
