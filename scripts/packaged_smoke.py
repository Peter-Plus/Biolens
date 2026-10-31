import asyncio
import json
import os
import subprocess
from pathlib import Path
import httpx

root = Path(__file__).resolve().parents[1]
release = root / "release" / json.loads((root/"package.json").read_text("utf-8"))["version"]

async def main():
    resource = release / "win-unpacked" / "resources"
    python = resource / "python" / "python.exe"
    env = dict(os.environ, BIOLENS_DATA=str(root / ".local" / "packaged-smoke"), BIOLENS_PORT="18765", BIOLENS_TOKEN="packaged-test-token", PLAYWRIGHT_BROWSERS_PATH=str(resource / "python" / "browsers"))
    p = subprocess.Popen([str(python), "-m", "biolens"], env=env, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            for _ in range(80):
                if p.poll() is not None:
                    raise RuntimeError(p.stderr.read().decode("utf-8", errors="replace")[-1500:])
                try:
                    response = await client.get("http://127.0.0.1:18765/health", headers={"Authorization":"Bearer packaged-test-token"})
                    if response.is_success:
                        break
                except httpx.RequestError:
                    pass
                await asyncio.sleep(.5)
            else:
                raise RuntimeError("Packaged backend timeout")
            assert (await client.get("http://127.0.0.1:18765/projects")).status_code == 401
            print("Packaged backend health and token gate: PASS", flush=True)
    finally:
        p.terminate()
        p.wait(timeout=10)
    env["BIOLENS_SCREENSHOT"] = str(root / "artifacts" / "ui" / "packaged-app.png")
    env.pop("ELECTRON_RUN_AS_NODE", None)
    app = subprocess.Popen([str(release / "win-unpacked" / "BioLens.exe")], env=env, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        await asyncio.to_thread(app.wait, 80)
        assert Path(env["BIOLENS_SCREENSHOT"]).exists(), "Desktop screenshot missing"
        print("Packaged Electron bootstrap and renderer: PASS", flush=True)
    finally:
        if app.poll() is None:
            app.terminate()

asyncio.run(main())
