import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load .env file
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")

print(f"SMTP_HOST: {SMTP_HOST}")
print(f"SMTP_PORT: {SMTP_PORT}")
print(f"SMTP_USER: {SMTP_USER}")
print(f"SMTP_FROM: {SMTP_FROM}")
print(f"SMTP_PASSWORD is set: {bool(SMTP_PASSWORD)}")

msg = MIMEMultipart("alternative")
msg["Subject"] = "FoxFlow Email Setup Test"
msg["From"] = f"FoxFlow <{SMTP_FROM}>"
msg["To"] = "skhjp2000@gmail.com"

text_body = "This is a test email from FoxFlow."
msg.attach(MIMEText(text_body, "plain"))

try:
    print("Connecting to SMTP server...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        print("Starting TLS...")
        server.starttls()
        print("Logging in...")
        server.login(SMTP_USER, SMTP_PASSWORD)
        print("Sending email...")
        server.sendmail(SMTP_FROM, ["skhjp2000@gmail.com"], msg.as_string())
        print("SUCCESS! Test email sent.")
except Exception as e:
    print(f"ERROR: {e}")
