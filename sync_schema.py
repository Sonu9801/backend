import sqlalchemy
from app.config import settings
from app.database import Base
import app.main  # ensures all routers and models are loaded

def run():
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = sqlalchemy.create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        for table_name, table in Base.metadata.tables.items():
            existing_columns = [
                row[0] for row in conn.execute(
                    sqlalchemy.text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'")
                ).fetchall()
            ]
            
            if not existing_columns:
                continue
                
            for column in table.columns:
                if column.name not in existing_columns:
                    col_type = column.type.compile(engine.dialect)
                    print(f"Adding missing column {column.name} ({col_type}) to {table_name}")
                    try:
                        conn.execute(sqlalchemy.text(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type};"))
                        conn.commit()
                        print(f"Success: Added {column.name} to {table_name}")
                    except Exception as e:
                        print(f"Failed to add {column.name} to {table_name}: {e}")
                        conn.rollback()

if __name__ == '__main__':
    run()
