import requests
import psycopg2

conn = psycopg2.connect("postgresql://postgres:Skhjp%402000@localhost:5432/Foxflow")
c = conn.cursor()
c.execute("SELECT email FROM users LIMIT 1")
row = c.fetchone()

if row:
    email = row[0]
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from app.auth import create_access_token
    token = create_access_token(data={"sub": email, "role": "admin"})
    
    res = requests.get("http://127.0.0.1:8000/api/auth/preferences", headers={"Authorization": f"Bearer {token}"})
    print("Status:", res.status_code)
    print("Response:", res.text)
else:
    print("No user found")
