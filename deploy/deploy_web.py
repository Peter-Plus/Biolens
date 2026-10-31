"""Deploy browser UI and isolated web executor, preserving the desktop cloud API."""
import tarfile
from pathlib import Path
from ssh import connect, ROOT

def run(client,command):
    _,out,err=client.exec_command(command,timeout=1800)
    for line in iter(out.readline,''):print(line.rstrip(),flush=True)
    errors=err.read().decode();code=out.channel.recv_exit_status()
    if errors:print(errors[-4000:],flush=True)
    if code:raise RuntimeError('Remote command failed: '+str(code))

archive=ROOT/'.local/web-deploy.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
    for p in (ROOT/'backend/biolens').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:tar.add(p,arcname='biolens/'+str(p.relative_to(ROOT/'backend/biolens')).replace('\\','/'))
    tar.add(ROOT/'deploy/Dockerfile.web',arcname='Dockerfile')
    tar.add(ROOT/'deploy/requirements-web.txt',arcname='requirements.txt')
    tar.add(ROOT/'dist',arcname='dist')
    tar.add(ROOT/'deploy/biolens-web.nginx',arcname='nginx.conf')
with connect() as client:
    run(client,'sudo -n install -d -o ubuntu -g ubuntu -m 750 /opt/biolens/web; sudo -n install -d -o 10001 -g 10001 -m 700 /var/lib/biolens-web; sudo -n docker network inspect biolens-net >/dev/null 2>&1 || sudo -n docker network create biolens-net; sudo -n docker network connect biolens-net biolens-cloud 2>/dev/null || true')
    with client.open_sftp() as sftp:sftp.put(str(archive),'/opt/biolens/web-deploy.tar.gz')
    run(client,'tar -xzf /opt/biolens/web-deploy.tar.gz -C /opt/biolens/web; sudo -n docker build -t biolens-web:0.3.0 /opt/biolens/web')
    run(client,'if sudo -n docker inspect biolens-web >/dev/null 2>&1; then sudo -n docker stop -t 30 biolens-web && sudo -n docker rm biolens-web; fi; sudo -n docker run -d --name biolens-web --network biolens-net --restart unless-stopped --memory 1800m --cpus 1.5 --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /tmp:rw,nosuid,size=384m --shm-size=256m -e BIOLENS_CLOUD_URL=http://biolens-cloud:8765 -p 127.0.0.1:8938:8766 -v /var/lib/biolens-web:/data biolens-web:0.3.0')
    run(client,'curl --retry 20 --retry-delay 2 --retry-all-errors -fsS http://127.0.0.1:8938/health')
    run(client,'sudo -n install -d -m 755 /var/www/biolens; sudo -n cp -r /opt/biolens/web/dist/. /var/www/biolens/; sudo -n chmod -R a+rX /var/www/biolens; sudo -n cp /etc/nginx/sites-available/biolens /opt/biolens/pre-web.nginx; sudo -n cp /opt/biolens/web/nginx.conf /etc/nginx/sites-available/biolens; sudo -n nginx -t && sudo -n systemctl reload nginx')
    run(client,'curl --retry 6 --retry-all-errors -fsS https://biolens.worldlinesite.com/web-api/health; curl -fsS https://biolens.worldlinesite.com/health')
print('Browser deployment completed.')
