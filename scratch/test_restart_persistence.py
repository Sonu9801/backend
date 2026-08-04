import sys
import os
import subprocess
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.session_store import session_store

try:
    print("Step 1: Creating session...")
    sid = session_store.create_session(user_id=12345, role="worker", ttl_days=1)
    print("Session created:", sid)
    
    # Verify it exists
    session = session_store.get_session(sid)
    print("Verification before restart:", session)
    if not session:
        print("ERROR: Session was not created.")
        sys.exit(1)
        
    print("Step 2: Restarting backend container...")
    # Run docker restart foxflow_backend
    subprocess.run(["docker", "restart", "foxflow_backend"], check=True)
    print("Container restarted. Waiting 3 seconds for uvicorn to start...")
    time.sleep(3)
    
    # Retrieve again
    print("Step 3: Retrieving session after restart...")
    # Re-initialize or re-import might be needed if script was running continuously,
    # but here we just call the store again. Note that the script runs on the host, 
    # and the redis container is STILL running (we only restarted foxflow_backend).
    # Since uvicorn restarted, we want to make sure it can still get the session,
    # and since we are on host we check if the session is still in Redis.
    session_after = session_store.get_session(sid)
    print("Verification after restart:", session_after)
    if session_after and session_after.get("user_id") == 12345:
        print("SUCCESS: Session persisted and was retrieved successfully after container restart!")
    else:
        print("FAILURE: Session lost after container restart.")
        
except Exception as e:
    print("ERROR:", e)
