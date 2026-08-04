import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.session_store import session_store

try:
    print("Creating session...")
    sid = session_store.create_session(user_id=999, role="worker", ttl_days=1)
    print("Created session ID:", sid)
    
    session = session_store.get_session(sid)
    print("Retrieved session details:", session)
    
    if session and session.get("user_id") == 999:
        print("SUCCESS: Session store is working correctly!")
    else:
        print("FAILURE: Session details mismatch or missing.")
        
except Exception as e:
    print("ERROR while running test:", e)
