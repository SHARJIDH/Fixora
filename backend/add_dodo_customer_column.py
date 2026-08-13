"""
Migration script to add dodoCustomerId column to user table.
This column is needed for Dodo Payments integration.
"""
import sys
from pathlib import Path

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR.parent / ".env")

from sqlalchemy import text
from services.db import get_db_session
from utils.logger import get_logger

logger = get_logger(__name__)

def add_dodo_customer_id_column():
    """Add dodoCustomerId column to user table if it doesn't exist."""
    with get_db_session() as session:
        try:
            # Check if column exists
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user' AND column_name = 'dodoCustomerId'
            """))
            
            if result.fetchone() is None:
                logger.info("Adding dodoCustomerId column to user table...")
                session.execute(text("""
                    ALTER TABLE "user" ADD COLUMN "dodoCustomerId" TEXT
                """))
                session.commit()
                logger.info("Successfully added dodoCustomerId column!")
            else:
                logger.info("dodoCustomerId column already exists.")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to add column: {e}")
            raise

if __name__ == "__main__":
    logger.info("Running Dodo Payments migration...")
    add_dodo_customer_id_column()
    logger.info("Migration complete!")
