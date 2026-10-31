"""Inspect credential-file structure without revealing credentials."""
from pathlib import Path
import re
from urllib.parse import urlsplit

file = Path(__file__).resolve().parents[2] / "key.txt"
text = file.read_text("utf-8-sig")
for i, line in enumerate(text.splitlines(), 1):
    urls = re.findall(r"https?://[^\s\"'<>]+", line)
    if urls:
        print(i, "endpoint", [urlsplit(u).hostname for u in urls])
    elif re.search(r"sk-|api.?key|secret|token", line, re.I):
        print(i, "credential [REDACTED]")
    elif len(line.strip()) > 35 and not re.search(r"model|模型", line, re.I):
        print(i, "long value [REDACTED]")
    else:
        print(i, line[:120])
