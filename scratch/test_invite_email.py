import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.email_utils import send_invite_email

print("Settings loaded:")
print(f"SMTP_HOST: {settings.SMTP_HOST}")
print(f"SMTP_PORT: {settings.SMTP_PORT}")
print(f"SMTP_USER: {settings.SMTP_USER}")
print(f"SMTP_FROM: {settings.SMTP_FROM}")
print(f"FRONTEND_URL: {settings.FRONTEND_URL}")

try:
    print("Sending test invitation email...")
    send_invite_email("skhjp2000@gmail.com", "Sonu Kumar", "manager")
    print("SUCCESS! Invite email sent successfully.")
except Exception as e:
    print(f"ERROR: {e}")
