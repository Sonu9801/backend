import sqlalchemy
from app.config import settings
from app.database import Base
import app.main

def run():
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            result = conn.execute(sqlalchemy.text("SELECT id, email, role, is_active, password FROM users")).fetchall()
            if not result:
                print("No users found in the database.")
            else:
                print("Users found:")
                for row in result:
                    has_password = bool(row[4])
                    print(f"ID: {row[0]}, Email: {row[1]}, Role: {row[2]}, Active: {row[3]}, Has Password: {has_password}")
        except Exception as e:
            print(f"Error querying users: {e}")

if __name__ == '__main__':
    run()
