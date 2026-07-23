import sqlite3
import sys

def run():
    conn = sqlite3.connect('foxflow.db')
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        print("Tables:", tables)
        if ('invoices',) in tables:
            print("Invoices table exists!")
            cur.execute("PRAGMA table_info(invoices);")
            print("Columns:", cur.fetchall())
        else:
            print("NO INVOICES TABLE!")
    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    run()
