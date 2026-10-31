"""Deploy only BioLens-owned files, never replace other sites or databases."""
from pathlib import Path
import sys,json,re
from ssh import connect,ROOT

def run(client,command):
    _,out,err=client.exec_command(command,timeout=600)
    for line in iter(out.readline,''):print(line.rstrip(),flush=True)
    errors=err.read().decode();code=out.channel.recv_exit_status()
    if errors:print(errors,flush=True)
    if code:raise RuntimeError('Deployment command failed, exit '+str(code))

with connect() as client:
    run(client,'sudo -n install -d -o ubuntu -g ubuntu -m 750 /opt/biolens /opt/biolens/build; sudo -n install -d -o 10001 -g 10001 -m 700 /var/lib/biolens; sudo -n install -d -m 755 /var/www/biolens-acme')
    with client.open_sftp() as sftp:
        for dirname in ['biolens','biolens_cloud']:
            try:sftp.mkdir('/opt/biolens/build/'+dirname)
            except IOError:pass
        files=[(ROOT/'deploy/Dockerfile','Dockerfile'),(ROOT/'deploy/requirements.txt','requirements.txt')]
        files += [(p,'biolens_cloud/'+p.name) for p in (ROOT/'backend/biolens_cloud').glob('*.py')]
        files += [(ROOT/'backend/biolens'/name,'biolens/'+name) for name in ['__init__.py','models.py','pubmed.py']]
        for local,remote in files:
            with sftp.open('/opt/biolens/build/'+remote,'w') as f:f.write(local.read_text('utf-8-sig').encode())
        keyfile=ROOT/'.local/app-data/settings.json';settings=json.loads(keyfile.read_text('utf-8'))
        # Never interpolate secrets into a command or Docker build context.
        env='BIOLENS_BASE_URL='+settings['base_url']+'\nBIOLENS_API_KEY='+settings['api_key']+'\n'
        with sftp.open('/opt/biolens/secrets.env','w') as f:f.write(env)
        sftp.chmod('/opt/biolens/secrets.env',0o600)
        with sftp.open('/opt/biolens/biolens.nginx','w') as f:f.write((ROOT/'deploy/biolens.nginx').read_text('utf-8-sig').encode())
    run(client,'sudo -n docker build -t biolens-cloud:0.2.0 /opt/biolens/build')
    run(client,'sudo -n docker network inspect biolens-net >/dev/null 2>&1 || sudo -n docker network create biolens-net')
    run(client,"if sudo -n docker inspect biolens-cloud >/dev/null 2>&1; then sudo -n docker stop biolens-cloud && sudo -n docker rm biolens-cloud; fi; sudo -n docker run -d --name biolens-cloud --network biolens-net --restart unless-stopped --memory 768m --cpus 1.5 --pids-limit 128 --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m -p 127.0.0.1:8937:8765 --env-file /opt/biolens/secrets.env -v /var/lib/biolens:/data biolens-cloud:0.2.0")
    run(client,'for n in $(seq 1 30); do curl -fsS http://127.0.0.1:8937/health && break; sleep 1; done; curl -fsS http://127.0.0.1:8937/health')
    # Bootstrap dedicated HTTP vhost for ACME, without changing other vhosts.
    bootstrap='server { listen 80; server_name biolens.worldlinesite.com; location /.well-known/acme-challenge/ { root /var/www/biolens-acme; } location / { proxy_pass http://127.0.0.1:8937; } }\n'
    with client.open_sftp() as sftp:
        with sftp.open('/opt/biolens/bootstrap.nginx','w') as f:f.write(bootstrap)
    run(client,'sudo -n cp /opt/biolens/bootstrap.nginx /etc/nginx/sites-available/biolens; sudo -n ln -sfn /etc/nginx/sites-available/biolens /etc/nginx/sites-enabled/biolens; sudo -n nginx -t && sudo -n systemctl reload nginx')
    run(client,'sudo -n certbot certonly --webroot -w /var/www/biolens-acme -d biolens.worldlinesite.com --non-interactive --agree-tos --register-unsafely-without-email --keep-until-expiring')
    run(client,'if test -f /opt/biolens/web/nginx.conf; then sudo -n cp /opt/biolens/web/nginx.conf /etc/nginx/sites-available/biolens; else sudo -n cp /opt/biolens/biolens.nginx /etc/nginx/sites-available/biolens; fi; sudo -n nginx -t && sudo -n systemctl reload nginx; curl --retry 6 --retry-delay 2 --retry-all-errors -fsS https://biolens.worldlinesite.com/health')
print('BioLens cloud deployment completed')
