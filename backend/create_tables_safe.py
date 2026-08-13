
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Load env from parent dir
load_dotenv(BASE_DIR.parent / ".env")

from services import db
from utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Initializing database (safe mode)...")
    db.init_db()
    logger.info("Database initialized.")
