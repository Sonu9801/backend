import sqlalchemy
from app.config import settings

def run():
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text("ALTER TABLE invoices ADD COLUMN file_hash VARCHAR;"))
            conn.execute(sqlalchemy.text("ALTER TYPE approvalstatus ADD VALUE IF NOT EXISTS 'Possible Duplicate';"))
            conn.commit()
            print("Columns added successfully.")
        except Exception as e:
            print("Error:", e)

if __name__ == '__main__':
    run()
