import requests

res = requests.get("http://127.0.0.1:8000/api/health")
print("Health:", res.status_code, res.json())

# Let's see if /api/auth/preferences requires token. It does. We'll get 401.
res2 = requests.get("http://127.0.0.1:8000/api/auth/preferences")
print("Preferences no token:", res2.status_code, res2.json())
