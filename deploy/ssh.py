"""Deployment-only SSH helper. Credentials stay in the user-supplied local file."""
import sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.local/ssh-libs'))
import paramiko

def connect():
 text=(ROOT.parent/'服务器.txt').read_text('utf-8-sig')
 password=re.search(r'^登录密码[：:]\s*(.+)$',text,re.M).group(1).strip()
 client=paramiko.SSHClient();client.load_system_host_keys()
 client.connect('129.226.116.120',username='ubuntu',password=password,look_for_keys=False,allow_agent=False,timeout=15)
 return client

if __name__=='__main__':
 with connect() as c:
  _,out,err=c.exec_command(sys.argv[1],timeout=180)
  print(out.read().decode());print(err.read().decode(),file=sys.stderr)
  sys.exit(out.channel.recv_exit_status())
