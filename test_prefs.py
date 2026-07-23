import requests

# 1. Login to get token
# Try to find a user in DB
import sqlite3
conn = sqlite3.connect("foxflow.db")
c = conn.cursor()
c.execute("SELECT email FROM users LIMIT 1")
row = c.fetchone()
if not row:
    print("No users found in SQLite!")
else:
    email = row[0]
    print(f"Testing with user: {email}")
    # Since login uses OTP, let's just create a token manually using auth.py logic
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from app.auth import create_access_token
    token = create_access_token(data={"sub": email, "role": "admin"})
    
    res = requests.get("http://127.0.0.1:8000/api/auth/preferences", headers={"Authorization": f"Bearer {token}"})
    print("Status:", res.status_code)
    print("Response:", res.text)
