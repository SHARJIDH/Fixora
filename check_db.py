import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("DATABASE_URL not found")
    sys.exit(1)

engine = create_engine(db_url)
with engine.connect() as conn:
    # Check columns in 'user' table
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'user'"))
    columns = [row[0] for row in result]
    print(f"Columns in 'user' table: {columns}")
    
    # Check if there are users with dodoCustomerId
    result = conn.execute(text('SELECT id, email, "dodoCustomerId" FROM "user" LIMIT 5'))
    users = result.fetchall()
    print(f"Sample users: {users}")
