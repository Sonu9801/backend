import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

def run_migration():
    print("Running migration for users table (adding preferences column)...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN preferences JSON;"))
            conn.commit()
            print("Successfully added preferences column to users table.")
        except Exception as e:
            if "already exists" in str(e) or "duplicate column name" in str(e).lower():
                print("Column 'preferences' already exists.")
            else:
                print(f"Error during migration: {e}")
                # Don't fail completely if SQLite doesn't support this specific alter table format perfectly,
                # though SQLite does support ADD COLUMN.

if __name__ == "__main__":
    run_migration()
