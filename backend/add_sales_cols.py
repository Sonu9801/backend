import asyncio
from sqlalchemy import text
from app.database import engine

queries = [
    "ALTER TABLE sales_invoices ADD COLUMN work_type VARCHAR NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN description_work_details VARCHAR NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN quantity FLOAT NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN unit VARCHAR NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN rate FLOAT NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN remarks VARCHAR NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN payment_date DATE NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN payment_mode VARCHAR NULL;",
    "ALTER TABLE sales_invoices ADD COLUMN transaction_reference VARCHAR NULL;",
    "CREATE INDEX IF NOT EXISTS ix_sales_invoices_work_type ON sales_invoices (work_type);"
]

with engine.connect() as conn:
    for q in queries:
        try:
            conn.execute(text(q))
            conn.commit()
            print(f"Executed: {q}")
        except Exception as e:
            conn.rollback()
            print(f"Failed: {q} - {e}")

print("Done")
