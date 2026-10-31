"""Configure a developer runtime; never add credentials to the repository."""
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
local = root / ".local"
local.mkdir(exist_ok=True)
data = local / "data"
data.mkdir(exist_ok=True)
config = {"python": sys.executable, "data": str(data), "browsers": str(local / "browsers")}
(local / "dev.json").write_text(json.dumps(config), "utf-8")
print("Developer runtime configured.")
