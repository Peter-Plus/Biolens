import {Download,ExternalLink} from 'lucide-react';
import {isWeb} from './api';
import {version} from '../package.json';

export default function PlatformLink(){
 const href=isWeb?`https://github.com/Peter-Plus/Biolens/releases/download/v${version}/BioLens-${version}-windows-x64.zip`:'https://biolens.worldlinesite.com/';
 return <a className="platform-link" href={href} target={isWeb?undefined:'_blank'} rel="noopener noreferrer" title={isWeb?'下载 Windows 客户端 ZIP，完整解压后使用':'在默认浏览器打开 BioLens'} onClick={event=>{if(window.biolens){event.preventDefault();void window.biolens.openExternal(href);}}}>
  {isWeb?<Download size={16}/>:<ExternalLink size={16}/>}<span>{isWeb?'下载客户端':'打开网页版'}</span>
 </a>;
}
