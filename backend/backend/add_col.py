from app.database import engine
from sqlalchemy import text
import sys

def main():
    with engine.connect() as con:
        try:
            con.execute(text('ALTER TABLE users ADD COLUMN dealer_name VARCHAR'))
            con.commit()
            print("Successfully added dealer_name column.")
        except Exception as e:
            print(f"Error (maybe column exists?): {e}")

if __name__ == '__main__':
    main()
