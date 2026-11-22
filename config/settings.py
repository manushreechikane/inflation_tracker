"""Runtime configuration. Reads .env once; everything else imports from here."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
RECEIPTS_DIR = DATA_DIR / "receipts"
PROCESSED_DIR = DATA_DIR / "processed"
CPI_DIR = DATA_DIR / "cpi"
LOG_DIR = BASE_DIR / "logs"

for _d in (DATA_DIR, RECEIPTS_DIR, PROCESSED_DIR, CPI_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{(DATA_DIR / 'inflationlens.db').as_posix()}"

# Secrets / machine-specific paths come from the environment only.
BLS_API_KEY = os.getenv("BLS_API_KEY", "")
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
POPPLER_PATH = os.getenv("POPPLER_PATH", "")

DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "IN")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "INR")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
RECEIPT_RETENTION_DAYS = int(os.getenv("RECEIPT_RETENTION_DAYS", "0"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "inflationlens.log"), logging.StreamHandler()],
)
