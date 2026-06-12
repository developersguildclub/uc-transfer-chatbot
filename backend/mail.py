import os
import smtplib
from email.message import EmailMessage


def mail_ready():
    port = os.getenv("MAIL_PORT")
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")

    if not os.getenv("MAIL_HOST") or not port or not os.getenv("MAIL_FROM"):
        return False

    if bool(username) != bool(password):
        return False

    try:
        int(port)
    except ValueError:
        return False

    return True


def send_mail(to_email, subject, body):
    host = os.getenv("MAIL_HOST")
    port = os.getenv("MAIL_PORT")
    from_email = os.getenv("MAIL_FROM")
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    use_tls = os.getenv("MAIL_USE_TLS", "true").lower() == "true"

    if not host or not port or not from_email:
        raise RuntimeError("Mail is not configured")

    if bool(username) != bool(password):
        raise RuntimeError("Mail credentials are incomplete")

    try:
        port_number = int(port)
    except ValueError:
        raise RuntimeError("Mail is not configured") from None

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(host, port_number) as smtp:
        if use_tls:
            smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
