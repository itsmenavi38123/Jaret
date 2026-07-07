import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
FROM_NAME = os.getenv("SMTP_FROM_NAME", "LightSignal")


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: str = None,
    from_name: str = None,
):
    sender_email = from_email or FROM_EMAIL
    sender_name = from_name or FROM_NAME

    if not all([SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, sender_email]):
        raise RuntimeError("SMTP email config missing")
    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(html_content, "html"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise RuntimeError(f"SMTP send failed: {str(e)}")
    print("DONE")
