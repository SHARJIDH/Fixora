import sys
import os
from pathlib import Path

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR.parent / ".env")

from services import db
from utils.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("Checking for missing database tables...")
    try:
        db.init_db()
        logger.info("Database tables checked/created.")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        sys.exit(1)
