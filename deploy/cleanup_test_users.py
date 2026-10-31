"""Remove only exact test accounts recorded by the local live verification script."""
import json
from ssh import connect,ROOT
users=json.loads((ROOT/'.local/cloud-test-users.json').read_text('utf-8'))
assert users and all(x['username'].startswith('verify_') for x in users)
script='''
import json,sqlite3
users=json.loads(PAYLOAD)
with sqlite3.connect('/data/cloud.sqlite3') as db:
 db.execute('PRAGMA foreign_keys=ON')
 for user in users:
  row=db.execute('SELECT username FROM users WHERE id=?',(user['id'],)).fetchone()
  if row is None:continue
  assert row[0]==user['username'] and row[0].startswith('verify_')
  for table in ['messages','chats','projects','sessions']:
   db.execute('DELETE FROM '+table+' WHERE user_id=?',(user['id'],))
  db.execute('DELETE FROM users WHERE id=?',(user['id'],))
 print('Removed verified test accounts:',len(users))
'''.replace('PAYLOAD',repr(json.dumps(users)))
with connect() as client:
 inp,out,err=client.exec_command('sudo -n docker exec -i biolens-cloud python -')
 inp.write(script);inp.channel.shutdown_write()
 print(out.read().decode());errors=err.read().decode()
 if out.channel.recv_exit_status():raise RuntimeError(errors)
 web_script="""
import json,re,sqlite3,shutil
from pathlib import Path
root=Path('/data')
for user in json.loads(PAYLOAD):
 assert user['username'].startswith('verify_') and re.fullmatch('[a-f0-9]{32}',user['id'])
 directory=root/'accounts'/user['id'];database=directory/'biolens.sqlite3'
 if database.exists():
  with sqlite3.connect(database) as db:run_ids=[r[0] for r in db.execute('SELECT id FROM runs')]
  for run_id in run_ids:
   assert re.fullmatch('[a-f0-9]{32}',run_id)
   artifact=(root/'artifacts'/run_id).resolve()
   assert artifact.parent==(root/'artifacts').resolve()
   if artifact.exists():shutil.rmtree(artifact)
 for parent in ['accounts','uploads']:
  target=(root/parent/user['id']).resolve()
  assert target.parent==(root/parent).resolve()
  if target.exists():shutil.rmtree(target)
print('Recorded web test workspaces removed.')
""".replace('PAYLOAD',repr(json.dumps(users)))
 _,check,_=client.exec_command('sudo -n docker inspect biolens-web >/dev/null 2>&1')
 if check.channel.recv_exit_status()==0:
  inp,out,err=client.exec_command('sudo -n docker exec -i biolens-web python -')
  inp.write(web_script);inp.channel.shutdown_write();print(out.read().decode())
  if out.channel.recv_exit_status():raise RuntimeError(err.read().decode())
 (ROOT/'.local/web-test-credentials.json').unlink(missing_ok=True)
 _,out,err=client.exec_command('sudo -n systemctl start biolens-backup.service')
 if out.channel.recv_exit_status():raise RuntimeError(err.read().decode())
print('Clean database backup created.')
