import urllib.request
import urllib.parse
import urllib.error

data = urllib.parse.urlencode({'username': '8287498867', 'password': '1234'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/api/auth/login', data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
try:
    print(urllib.request.urlopen(req).read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(e.code, e.read().decode('utf-8'))
