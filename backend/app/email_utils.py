import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_otp_email(to_email: str, otp_code: str, user_name: str = "User"):
    """Send an OTP verification email via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"FoxFlow - Your Login OTP: {otp_code}"
    msg["From"] = f"FoxFlow <{settings.SMTP_FROM}>"
    msg["To"] = to_email

    html_body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #0a0a0f; color: #e4e4e7; padding: 40px 0;">
      <div style="max-width: 480px; margin: 0 auto; background: linear-gradient(135deg, #18181b 0%, #1c1c22 100%); border-radius: 16px; border: 1px solid #27272a; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%); padding: 32px 32px 24px;">
          <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">FOXFLOW</h1>
          <p style="margin: 8px 0 0; font-size: 14px; color: rgba(255,255,255,0.8);">Manufacturing Command Center</p>
        </div>
        <div style="padding: 32px;">
          <p style="font-size: 16px; color: #a1a1aa; margin: 0 0 8px;">Hello <strong style="color: #e4e4e7;">{user_name}</strong>,</p>
          <p style="font-size: 14px; color: #a1a1aa; margin: 0 0 24px; line-height: 1.6;">
            Use the verification code below to sign in to your FoxFlow account. This code expires in <strong style="color: #e4e4e7;">5 minutes</strong>.
          </p>
          <div style="background: #09090b; border: 1px solid #27272a; border-radius: 12px; padding: 24px; text-align: center; margin: 0 0 24px;">
            <span style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #7c3aed; font-family: 'Courier New', monospace; white-space: nowrap;">{otp_code}</span>
          </div>
          <p style="font-size: 12px; color: #71717a; margin: 0; line-height: 1.5;">
            If you did not request this code, please ignore this email. Do not share this code with anyone.
          </p>
        </div>
        <div style="padding: 16px 32px; border-top: 1px solid #27272a; text-align: center;">
          <p style="font-size: 11px; color: #52525b; margin: 0;">&copy; {2025} Fox Enterprises. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """

    text_body = f"Hello {user_name},\n\nYour FoxFlow OTP is: {otp_code}\n\nThis code expires in 5 minutes.\n\nDo not share this code with anyone."

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())


def send_invite_email(to_email: str, user_name: str, role: str):
    """Send an invitation email via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"FoxFlow - You have been invited as {role.capitalize()}"
    msg["From"] = f"FoxFlow <{settings.SMTP_FROM}>"
    msg["To"] = to_email

    html_body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #0a0a0f; color: #e4e4e7; padding: 40px 0;">
      <div style="max-width: 480px; margin: 0 auto; background: linear-gradient(135deg, #18181b 0%, #1c1c22 100%); border-radius: 16px; border: 1px solid #27272a; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%); padding: 32px 32px 24px;">
          <h1 style="margin: 0; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">FOXFLOW</h1>
          <p style="margin: 8px 0 0; font-size: 14px; color: rgba(255,255,255,0.8);">Manufacturing Command Center</p>
        </div>
        <div style="padding: 32px;">
          <p style="font-size: 16px; color: #a1a1aa; margin: 0 0 8px;">Hello <strong style="color: #e4e4e7;">{user_name}</strong>,</p>
          <p style="font-size: 14px; color: #a1a1aa; margin: 0 0 24px; line-height: 1.6;">
            You have been invited to join FoxFlow as a <strong>{role.capitalize()}</strong>.
          </p>
          <p style="font-size: 14px; color: #a1a1aa; margin: 0 0 24px; line-height: 1.6;">
            You can log in to the portal using this email address. Your login will be authenticated using a One-Time Password (OTP) sent to this email.
          </p>
        </div>
        <div style="padding: 16px 32px; border-top: 1px solid #27272a; text-align: center;">
          <p style="font-size: 11px; color: #52525b; margin: 0;">&copy; 2026 Fox Enterprises. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """

    text_body = f"Hello {user_name},\n\nYou have been invited to join FoxFlow as a {role.capitalize()}.\n\nYou can log in using this email address via OTP."

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
