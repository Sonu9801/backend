import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine

def run_migration():
    print("Running migration for factory_settings table...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS factory_settings (
                id SERIAL PRIMARY KEY,
                facility_name VARCHAR NOT NULL,
                address VARCHAR NOT NULL,
                operating_hours VARCHAR NOT NULL,
                timezone VARCHAR NOT NULL,
                departments JSON NOT NULL
            );
        """))
        conn.commit()
    print("Migration completed.")

if __name__ == "__main__":
    run_migration()
