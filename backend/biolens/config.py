import json
import os
from pathlib import Path

DATA_DIR = Path(os.getenv("BIOLENS_DATA", str(Path.home() / ".biolens"))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = DATA_DIR / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def read_settings():
    file = DATA_DIR / "settings.json"
    value = json.loads(file.read_text("utf-8")) if file.exists() else {}
    return {"base_url": os.getenv("BIOLENS_BASE_URL", value.get("base_url", "")),
            "model": os.getenv("BIOLENS_MODEL", value.get("model") or "qwen3.7-flash"),
            "api_key": os.getenv("BIOLENS_API_KEY", value.get("api_key", ""))}


def save_settings(value):
    current = read_settings()
    for key in ("base_url", "model", "api_key"):
        if key in value and value[key] is not None:
            current[key] = value[key].strip()
    (DATA_DIR / "settings.json").write_text(json.dumps(current, ensure_ascii=False), "utf-8")


def public_settings():
    v = read_settings()
    return {"base_url": v["base_url"], "model": v["model"], "has_key": bool(v["api_key"])}
