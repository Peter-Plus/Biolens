#!/bin/sh
set -eu
# SQLite online backup includes committed WAL data and runs inside the app container.
docker exec -i biolens-cloud python - <<'PY'
import sqlite3,datetime
from pathlib import Path
folder=Path('/data/backups');folder.mkdir(exist_ok=True)
name=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
with sqlite3.connect('/data/cloud.sqlite3') as source, sqlite3.connect(folder/(name+'.sqlite3')) as target:
    source.backup(target)
for old in sorted(folder.glob('*.sqlite3'))[:-7]:old.unlink()
PY

# Web account databases use SQLite snapshots; uploads/reports are backed up separately.
if docker inspect biolens-web >/dev/null 2>&1; then
docker exec -i biolens-web python - <<'PYWEB'
import sqlite3,datetime,tarfile,tempfile
from pathlib import Path
root=Path('/data');folder=root/'backups';folder.mkdir(exist_ok=True)
name=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp)
    with tarfile.open(folder/(name+'.tar.gz'),'w:gz') as tar:
        for db in (root/'accounts').glob('*/biolens.sqlite3'):
            target=temp/db.parent.name;target.mkdir()
            with sqlite3.connect(db) as src,sqlite3.connect(target/db.name) as dst:src.backup(dst)
            tar.add(target/db.name,arcname='accounts/'+db.parent.name+'/'+db.name)
        for name in ['uploads','artifacts']:
            if (root/name).exists():tar.add(root/name,arcname=name)
for old in sorted(folder.glob('*.tar.gz'))[:-7]:old.unlink()
PYWEB
fi
