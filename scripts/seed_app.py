"""Prepare a clean local demo workspace; never included in distribution."""
import json
import shutil
from pathlib import Path
from biolens.config import DATA_DIR
from biolens import store

root = Path(__file__).resolve().parents[1]
target = root / ".local" / "app-data"
target.mkdir(parents=True, exist_ok=True)
settings = DATA_DIR / "settings.json"
if settings.exists():
    shutil.copy2(settings, target / "settings.json")
# Future local launches use a clean workspace, separate from evaluation runs.
cfg = json.loads((root / ".local" / "dev.json").read_text("utf-8"))
cfg["data"] = str(target)
(root / ".local" / "dev.json").write_text(json.dumps(cfg), "utf-8")
print("Clean local application settings prepared; key not displayed.")
