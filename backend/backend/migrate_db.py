import sqlite3

def run():
    print("Connecting to foxflow.db")
    conn = sqlite3.connect('foxflow.db')
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE invoices ADD COLUMN file_hash VARCHAR;")
        print("Column file_hash added successfully.")
    except Exception as e:
        print("Error:", e)
    finally:
        conn.commit()
        conn.close()

if __name__ == '__main__':
    run()
