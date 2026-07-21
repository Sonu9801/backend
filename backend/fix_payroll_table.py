import psycopg2
from app.config import settings

def fix_table():
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    columns_to_add = [
        "leave_days FLOAT DEFAULT 0.0",
        "working_hours FLOAT DEFAULT 0.0",
        "sunday_work FLOAT DEFAULT 0.0",
        "days_absent FLOAT DEFAULT 0.0",
        "days_present FLOAT DEFAULT 0.0",
        "half_days FLOAT DEFAULT 0.0",
        "late_count INTEGER DEFAULT 0",
        "holiday_work FLOAT DEFAULT 0.0",
        "ot_hours FLOAT DEFAULT 0.0",
        "net_working_days FLOAT DEFAULT 0.0"
    ]
    for col in columns_to_add:
        col_name = col.split()[0]
        try:
            print(f"Adding column {col_name}...")
            cur.execute(f"ALTER TABLE payroll_records ADD COLUMN {col}")
            conn.commit()
            print(f"Added column {col_name} successfully.")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print(f"Column {col_name} already exists.")
        except Exception as e:
            conn.rollback()
            print(f"Error adding {col_name}: {e}")
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_table()
