from ssh import connect,ROOT
with connect() as c:
 with c.open_sftp() as s:
  for name in ['backup.sh','biolens-backup.service','biolens-backup.timer']:
   with s.open('/opt/biolens/'+name,'w') as f:f.write((ROOT/'deploy'/name).read_text('utf-8-sig').replace('\r\n','\n'))
 _,out,err=c.exec_command('sudo -n cp /opt/biolens/biolens-backup.service /etc/systemd/system/biolens-backup.service && sudo -n cp /opt/biolens/biolens-backup.timer /etc/systemd/system/biolens-backup.timer && sudo -n systemctl daemon-reload && sudo -n systemctl enable --now biolens-backup.timer && sudo -n systemctl start biolens-backup.service && sudo -n systemctl is-active biolens-backup.timer; sudo -n ls /var/lib/biolens/backups',timeout=60)
 print(out.read().decode());print(err.read().decode());assert out.channel.recv_exit_status()==0
