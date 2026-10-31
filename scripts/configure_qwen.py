from pathlib import Path
import re
from biolens.config import save_settings

file = Path(__file__).resolve().parents[2] / "key.txt"
match = re.search(r"sk-[A-Za-z0-9_.-]+", file.read_text("utf-8-sig"))
if not match:
    raise SystemExit("没有识别到密钥，请在设置中填写。")
save_settings({"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen3.7-flash", "api_key": match.group(0)})
print("Qwen configuration saved locally; key not displayed.")
