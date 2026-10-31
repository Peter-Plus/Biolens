"""Only diagnostic categories and lengths, never credentials."""
import asyncio
import re
from pathlib import Path
import httpx
from biolens.config import read_settings

async def main():
    cfg = read_settings()
    raw = (Path(__file__).resolve().parents[2] / "key.txt").read_text("utf-8-sig").strip()
    print({"file_characters": len(raw), "parsed_characters": len(cfg["api_key"]), "exact_match": raw == cfg["api_key"], "non_ascii_count": sum(ord(c)>127 for c in raw), "model": cfg["model"]})
    async with httpx.AsyncClient(timeout=35) as client:
        r = await client.post(cfg["base_url"]+"/chat/completions", headers={"Authorization": "Bearer "+cfg["api_key"]},json={"model": cfg["model"], "messages":[{"role":"user","content":"只回答连接成功"}],"enable_thinking":False})
        print("HTTP",r.status_code)
        if r.is_success:
            print(r.json()["choices"][0]["message"]["content"])
        else:
            code = r.json().get("error",{}).get("code", "unknown")
            print("Provider error code:", re.sub(r"[^A-Za-z0-9_.-]", "", str(code))[:80])
asyncio.run(main())
