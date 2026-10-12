import os, sys
sys.path.insert(0, os.path.abspath("."))
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    tables = [row[0] for row in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")).fetchall()]
    for table in tables:
        cols = [c[0] for c in conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND data_type IN ('text', 'character varying');")).fetchall()]
        conditions = [f'"{col}"::text LIKE \'%554%\' OR "{col}"::text LIKE \'%556%\'' for col in cols]
        if conditions:
            query = f'SELECT * FROM "{table}" WHERE {" OR ".join(conditions)}'
            rows = conn.execute(text(query)).fetchall()
            if rows:
                print(f"=== Found in {table} ({len(rows)} rows) ===")
                for r in rows:
                    print(r)
