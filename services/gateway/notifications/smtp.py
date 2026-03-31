"""Email notification via SMTP (async)."""
from __future__ import annotations
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SMTPNotifier:
    """Sends HTML emails via SMTP with STARTTLS."""

    def __init__(
        self, host: Optional[str] = None, port: int = 587,
        username: Optional[str] = None, password: Optional[str] = None,
        from_address: Optional[str] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_address = from_address or "variance-agent@company.com"

    async def send(
        self, to: list[str], subject: str, html_body: str, *,
        cc: Optional[list[str]] = None,
        attachments: Optional[list[str]] = None,
    ) -> bool:
        if not self.host:
            logger.warning("SMTP: no host configured")
            return False
        if not to:
            logger.warning("SMTP: no recipients")
            return False

        # Build MIME message
        msg = MIMEMultipart("mixed")
        msg["From"] = self.from_address
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)

        msg.attach(MIMEText(html_body, "html"))

        # Attach files
        if attachments:
            for filepath in attachments:
                path = Path(filepath)
                if path.exists():
                    with open(path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=path.name)
                        part["Content-Disposition"] = f'attachment; filename="{path.name}"'
                        msg.attach(part)

        # Send via aiosmtplib (or fallback to smtplib)
        try:
            try:
                import aiosmtplib
                smtp = aiosmtplib.SMTP(hostname=self.host, port=self.port, use_tls=False)
                await smtp.connect()
                if self.port == 587:
                    await smtp.starttls()
                if self.username and self.password:
                    await smtp.login(self.username, self.password)
                all_recipients = to + (cc or [])
                await smtp.send_message(msg, sender=self.from_address, recipients=all_recipients)
                await smtp.quit()
                return True
            except ImportError:
                # Fallback to synchronous smtplib
                import smtplib
                with smtplib.SMTP(self.host, self.port) as smtp_conn:
                    if self.port == 587:
                        smtp_conn.starttls()
                    if self.username and self.password:
                        smtp_conn.login(self.username, self.password)
                    all_recipients = to + (cc or [])
                    smtp_conn.send_message(msg, from_addr=self.from_address, to_addrs=all_recipients)
                return True
        except Exception as exc:
            logger.error("SMTP send failed: %s", exc)
            return False
