import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from app.config import settings


def send_otp_email(to_email: str, otp_code: str, user_name: str = "User"):
    """Send an OTP verification email via Gmail SMTP with headers to avoid spam folder."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"FoxFlow - Your Login OTP: {otp_code}"
    msg["From"] = f"FoxFlow <{settings.SMTP_FROM}>"
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="foxflow.internal")
    msg["MIME-Version"] = "1.0"

    html_body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f4f4f5; color: #1f2937; padding: 40px 10px; margin: 0;">
      <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e4e4e7; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <div style="background-color: #7c3aed; padding: 32px; text-align: center;">
          <h1 style="margin: 0; font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">FOXFLOW</h1>
          <p style="margin: 4px 0 0; font-size: 13px; color: #e9d5ff; text-transform: uppercase; font-weight: 600; letter-spacing: 1px;">Manufacturing Command Center</p>
        </div>
        <div style="padding: 32px;">
          <p style="font-size: 16px; color: #374151; margin: 0 0 12px;">Hello <strong>{user_name}</strong>,</p>
          <p style="font-size: 14px; color: #4b5563; margin: 0 0 24px; line-height: 1.6;">
            Use the verification code below to sign in to your FoxFlow account. This code is valid for <strong>5 minutes</strong>.
          </p>
          <div style="background-color: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; text-align: center; margin: 0 0 24px;">
            <span style="font-size: 34px; font-weight: 800; letter-spacing: 6px; color: #7c3aed; font-family: 'Courier New', Courier, monospace; white-space: nowrap;">{otp_code}</span>
          </div>
          <p style="font-size: 12px; color: #9ca3af; margin: 0; line-height: 1.5; text-align: center;">
            This is an automated security code. Please do not share it with anyone.
          </p>
        </div>
        <div style="padding: 16px 32px; background-color: #fafafa; border-top: 1px solid #f3f4f6; text-align: center;">
          <p style="font-size: 11px; color: #9ca3af; margin: 0;">&copy; 2026 Fox Enterprises. All rights reserved.</p>
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
    """Send an invitation email via Gmail SMTP with headers to avoid spam folder."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"FoxFlow - You have been invited as {role.capitalize()}"
    msg["From"] = f"FoxFlow <{settings.SMTP_FROM}>"
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="foxflow.internal")
    msg["MIME-Version"] = "1.0"

    invite_url = f"{settings.FRONTEND_URL}/login?email={to_email}&invite=true"

    html_body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f4f4f5; color: #1f2937; padding: 40px 10px; margin: 0;">
      <div style="max-width: 500px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; border: 1px solid #e4e4e7; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
        <div style="background-color: #7c3aed; padding: 32px; text-align: center;">
          <h1 style="margin: 0; font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">FOXFLOW</h1>
          <p style="margin: 4px 0 0; font-size: 13px; color: #e9d5ff; text-transform: uppercase; font-weight: 600; letter-spacing: 1px;">Manufacturing Command Center</p>
        </div>
        <div style="padding: 32px; text-align: left;">
          <p style="font-size: 16px; color: #374151; margin: 0 0 12px;">Hello <strong>{user_name}</strong>,</p>
          <p style="font-size: 14px; color: #4b5563; margin: 0 0 20px; line-height: 1.6;">
            You have been invited by your administrator to join the FoxFlow ERP command center as a <strong>{role.capitalize()}</strong>.
          </p>
          <p style="font-size: 14px; color: #4b5563; margin: 0 0 28px; line-height: 1.6;">
            Click the button below to set up your password and complete your registration:
          </p>
          <div style="text-align: center; margin: 24px 0;">
            <a href="{invite_url}" style="background-color: #7c3aed; color: #ffffff; padding: 12px 30px; text-decoration: none; font-weight: 600; border-radius: 6px; font-size: 14px; display: inline-block; box-shadow: 0 4px 10px rgba(124, 58, 237, 0.2);">
              Complete Setup
            </a>
          </div>
          <p style="font-size: 12px; color: #9ca3af; line-height: 1.6; margin: 24px 0 0;">
            If the button doesn't work, copy and paste this link in your browser:<br/>
            <a href="{invite_url}" style="color: #7c3aed; text-decoration: underline;">{invite_url}</a>
          </p>
          <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #f3f4f6; font-size: 11px; color: #9ca3af; line-height: 1.5;">
            <strong>Security Note:</strong> This is a secure system registration link requested by an authorized administrator of your enterprise. Do not forward this email to anyone.
          </div>
        </div>
        <div style="padding: 16px 32px; background-color: #fafafa; border-top: 1px solid #f3f4f6; text-align: center;">
          <p style="font-size: 11px; color: #9ca3af; margin: 0;">&copy; 2026 Fox Enterprises. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """

    text_body = f"Hello {user_name},\n\nYou have been invited to join FoxFlow as a {role.capitalize()}.\n\nPlease visit this link to set your password and complete your registration:\n{invite_url}"

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
