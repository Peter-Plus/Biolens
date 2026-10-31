"""Package isolated Python and browser for Windows. No user data or keys copied."""
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / "runtime" / "python"
target.mkdir(parents=True, exist_ok=True)
archive = root / ".local" / "python-embed.zip"
if not archive.exists():
    urllib.request.urlretrieve("https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip", archive)
if not (target / "python.exe").exists():
    with zipfile.ZipFile(archive) as z:
        z.extractall(target)
(target / "python312._pth").write_text("python312.zip\n.\nLib/site-packages\n../backend\nimport site\n", "utf-8")
exclude = shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "test", "pip", "Scripts")
shutil.copytree(root / ".local" / "pylibs", target / "Lib" / "site-packages", dirs_exist_ok=True, ignore=exclude)
shutil.copytree(root / ".local" / "browsers", target / "browsers", dirs_exist_ok=True)
print("Portable Python and browser prepared; credentials excluded.")
