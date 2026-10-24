from pathlib import Path
from dotenv import load_dotenv
import sys

ROOT = Path(__file__).resolve().parent
load_dotenv(r"C:\Users\gupta\OneDrive\Desktop\fitness-tracker\.env")
sys.path.insert(0, str(ROOT / "backend"))
from app import app

app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
