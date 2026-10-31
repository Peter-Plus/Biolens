import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run("biolens.api:app", host="127.0.0.1", port=int(os.getenv("BIOLENS_PORT", "8765")), log_level="warning")
