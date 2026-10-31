import os
from pathlib import Path
import uuid
root = Path(__file__).resolve().parents[2]
os.environ["BIOLENS_DATA"] = str(root / ".local" / "test-data" / uuid.uuid4().hex)
