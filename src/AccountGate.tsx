import {useEffect,useState,ReactNode} from 'react';
import {api,connect,isWeb} from './api';
import PlatformLink from './PlatformLink';
import logo from '../assets/logo.svg';
export type Account={enabled:boolean;user:{id:string;username:string}|null;server:string};
export default function AccountGate({children}:{children:(account:Account)=>ReactNode}){
 const [account,setAccount]=useState<Account|null>(null),[register,setRegister]=useState(false),[username,setUsername]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{connect().then(()=>api<Account>('/account')).then(setAccount).catch(e=>setError(e.message));},[]);
 async function submit(){setBusy(true);setError('');try{setAccount(await api<Account>('/account/'+(register?'register':'login'),'POST',{username,password}));setPassword('');}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 if(account&&(!account.enabled||account.user))return children(account);
 return <main className="auth-page"><section className="auth-intro"><img src={logo} alt="BioLens"/><h1>{isWeb?'打开浏览器，':'数据在本地，'}<br/>研究持续连接。</h1><p>{isWeb?'与桌面版共用账号和聊天。上传项目资料，在云端分析并生成可下载的报告。':'账号保存项目名称和聊天记录。项目文件、数据计算与可视化报告留在当前电脑。'}</p><p>用于回答的资料片段和分析摘要会发送至云端模型服务。</p></section><form className="auth-form" onSubmit={e=>{e.preventDefault();submit();}}><h2>{register?'创建 BioLens 账号':'登录 BioLens'}</h2><p>biolens.worldlinesite.com</p><label>用户名<input autoComplete="username" required pattern="[A-Za-z0-9_]{3,32}" minLength={3} maxLength={32} value={username} onChange={e=>setUsername(e.target.value)} placeholder="3–32 位字母、数字或下划线"/></label><label>密码<input type="password" autoComplete={register?'new-password':'current-password'} required minLength={10} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)} placeholder="至少 10 个字符"/></label>{error&&<p role="alert" className="error">{error}</p>}<button className="primary" disabled={busy||!account}>{busy?'正在连接…':register?'注册并登录':'登录'}</button><button type="button" className="auth-switch" onClick={()=>{setRegister(!register);setError('');}}>{register?'已有账号，返回登录':'还没有账号？注册'}</button><PlatformLink/></form></main>;
}
