import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    def _base_message(self, *, to_email: str, subject: str) -> EmailMessage:
        settings = get_settings()
        from_email = settings.smtp_from_email or settings.smtp_user
        if not from_email:
            from_email = "no-reply@suswastha.local"
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"SuSwastha <{from_email}>"
        message["To"] = to_email
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
        message["Reply-To"] = from_email
        message["X-Auto-Response-Suppress"] = "All"
        return message

    def _send(self, message: EmailMessage) -> None:
        settings = get_settings()
        if not (settings.smtp_user and settings.smtp_password):
            logger.info("email_skipped_smtp_not_configured", extra={"to_email": message["To"]})
            return
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)

    def send_otp_email(self, *, to_email: str, otp: str, purpose: str) -> None:
        message = self._base_message(to_email=to_email, subject="Your SuSwastha verification code")
        message.set_content(
            f"Your SuSwastha verification code is {otp}.\n\n"
            "It expires in 5 minutes. If you did not request this, you can ignore this email.\n\n"
            "SuSwastha"
        )
        message.add_alternative(
            f"""
            <html>
              <body>
                <p>Your SuSwastha verification code is:</p>
                <p style="font-size:24px;letter-spacing:4px"><strong>{otp}</strong></p>
                <p>This code expires in 5 minutes.</p>
              </body>
            </html>
            """,
            subtype="html",
        )
        self._send(message)

    def send_report_email(self, *, to_email: str, test_type: str, pdf_url: str) -> None:
        message = self._base_message(to_email=to_email, subject="Your SuSwastha Health Report")
        message.set_content(
            "Your SuSwastha health report is ready.\n\n"
            f"Secure report link: {pdf_url}\n\n"
            "This educational risk estimate is not a diagnosis. Please consult a clinician."
        )
        message.add_alternative(
            f"""
            <html>
              <body>
                <p>Your SuSwastha health report is ready.</p>
                <p><a href="{pdf_url}">Open your secure report</a></p>
                <p>This educational risk estimate is not a diagnosis. Please consult a clinician.</p>
              </body>
            </html>
            """,
            subtype="html",
        )
        self._send(message)
