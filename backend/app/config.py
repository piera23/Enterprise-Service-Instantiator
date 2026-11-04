import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

DATA_DIR.mkdir(parents=True, exist_ok=True)
INSTANCES_FILE = DATA_DIR / "instances.json"
